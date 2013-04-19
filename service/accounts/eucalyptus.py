"""
UserManager:
  Remote Eucalyptus Admin controls..

User, BooleanField, StringList
  These XML parsing classes belong to euca_admin.py,
  and can be found on the Cloud Controller
"""
from django.contrib.auth.models import User
from django.db.models import Max

from atmosphere import settings
from atmosphere.logger import logger
from core.models.identity import Identity
from core.models.group import Group, IdentityMembership, ProviderMembership
from core.models.provider import Provider
from core.models.credential import Credential
from core.models.quota import Quota
from service.drivers.eucalyptusUserManager import UserManager


class AccountDriver():
    user_manager = None
    euca_prov = None

    def __init__(self):
        self.user_manager = UserManager()
        self.euca_prov = Provider.objects.get(location='EUCALYPTUS')

    def create_account(self, username):
        euca_user = self.get_user(username)
        identity = self.create_identity(euca_user)

    def create_identity(self, euca_user, max_quota=False):
        """
        euca_user - A dictionary containing 'access_key', 'secret_key', and 'username'
        max_quota - Set this user to have the maximum quota, instead of the
        default quota
        """
        (user, group) = self.create_usergroup(euca_user['username'])
        try:
            id_membership = IdentityMembership.objects.get(
                identity__provider=self.euca_prov,
                member__name=user.username,
                identity__created_by__username=user.username)
            if max_quota:
                quota = self.get_max_quota()
                id_membership.quota = quota
                id_membership.save()
            return id_membership.identity
        except IdentityMembership.DoesNotExist:
            logger.debug(euca_user)
            #Provider Membership
            p_membership = ProviderMembership.objects.get_or_create(
                provider=self.euca_prov, member=group)[0]

            #Identity Membership
            identity = Identity.objects.get_or_create(
                created_by=user, provider=self.euca_prov)[0]

            Credential.objects.get_or_create(
                identity=identity, key='key',
                value=euca_user['access_key'])[0]
            Credential.objects.get_or_create(
                identity=identity, key='secret',
                value=euca_user['secret_key'])[0]

            if max_quota:
                quota = self.get_max_quota()
            else:
                default_quota = Quota().defaults()
                quota = Quota.objects.filter(cpu=default_quota['cpu'],
                                             memory=default_quota['memory'],
                                             storage=default_quota['storage']
                                            )[0]

            #Link it to the usergroup -- Don't create more than one membership
            try:
                id_membership = IdentityMembership.objects.get(
                    identity=identity, member=group)
                id_membership.quota = quota
                id_membership.save()
            except IdentityMembership.DoesNotExist:
                id_membership = IdentityMembership.objects.create(
                    identity=identity, member=group,
                    quota=quota)
            except IdentityMembership.MultipleObjectReturned:
                #No dupes
                IdentityMembership.objects.filter(
                    identity=identity, member=group).delete()
                #Create one with new quota
                id_membership = IdentityMembership.objects.create(
                    identity=identity, member=group,
                    quota=quota)

            #Return the identity
            return id_membership.identity
    def add_user(self, username):
        userCreated = self.user_manager.add_user(username)
        if not userCreated:
            return None
        user = self.user_manager.get_user(username)
        return user

    def delete_user(self, username):
        userDeleted = self.user_manager.delete_user(username)
        return userDeleted

    def create_usergroup(self, username):
        user = User.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=username)[0]

        user.groups.add(group)
        user.save()
        group.leaders.add(user)
        group.save()
        return (user, group)

    def get_max_quota(self):
        max_quota_by_cpu = Quota.objects.all().aggregate(Max('cpu')
                                                           )['cpu__max']
        quota = Quota.objects.filter(cpu=max_quota_by_cpu)
        return quota[0]

    def get_key(self, user):
        return self.user_manager.get_key(user)

    def get_keys(self, userList):
        return self.user_manager.get_keys(userList)

    def get_user(self, user):
        return self.user_manager.get_user(user)

    def get_users(self, userList):
        return self.user_manager.get_users(userList)

    def list_users(self):
        return self.user_manager.get_all_users()
