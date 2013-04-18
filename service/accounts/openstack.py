"""
UserManager:
  Remote Openstack  Admin controls..
"""
from hashlib import sha1

from django.contrib.auth.models import User

from novaclient.v1_1 import client as nova_client

from atmosphere import settings
from atmosphere.logger import logger

from core.models.identity import Identity
from core.models.group import Group, IdentityMembership, ProviderMembership
from core.models.provider import Provider
from core.models.credential import Credential
from core.models.quota import Quota

from service.drivers.openstackUserManager import UserManager
from service.drivers.openstackNetworkManager import NetworkManager


class AccountDriver():
    user_manager = None
    openstack_prov = None

    def __init__(self, *args, **kwargs):
        self.user_manager = UserManager.settings_init()
        self.network_manager = NetworkManager.settings_init()
        self.openstack_prov = Provider.objects.get(location='OPENSTACK')

    def get_or_create_user(self, username, password=None,
                           usergroup=True, admin=False):
        user = self.get_user(username)
        if user:
            return user
        user = self.create_user(username, password, usergroup, admin)
        return user

    def create_user(self, username, password=None, usergroup=True, admin=False,):
        if not password:
            password = self.hashpass(username)
        if usergroup:
            (tenant, user, role) = self.user_manager.add_usergroup(username,
                                                                  password,
                                                                  True,
                                                                  admin)
            logger.info("Creating network for %s" % username)
        else:
            user = self.user_manager.add_user(username, password)
            tenant = self.user_manager.get_tenant(username)
        #TODO: Instead, return user.get_user match, or call it if you have to..
        return user

    def delete_user(self, username, usergroup=True, admin=False):
        tenant = self.user_manager.get_tenant(username)
        if tenant:
            self.network_manager.delete_tenant_network(username, tenant.name)
        if usergroup:
            deleted = self.user_manager.delete_usergroup(username)
        else:
            deleted = self.user_manager.delete_user(username)
        return deleted

    def create_usergroup(self, username):
        user = User.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=username)[0]

        user.groups.add(group)
        user.save()
        group.leaders.add(user)
        group.save()
        return (user, group)

    def get_max_quota():
        max_quota_by_cpu = Quota.objects.all().aggregate(Max('cpu')
                                                           )['cpu__max']
        quota = Quota.objects.filter(cpu=max_quota_by_cpu)
        return quota[0]

    def create_openstack_identity(self, username, password, tenant_name, max_quota=False):
        #Get the usergroup
        (user, group) = self.create_usergroup(username)
        try:
            id_membership = IdentityMembership.objects.filter(
                identity__provider=self.openstack_prov,
                member__name=username,
                identity__credential__value__in=[
                    username, password, tenant_name]).distinct()[0]
            Credential.objects.get_or_create(
                identity=id_member.identity,
                key='ex_tenant_name', value=tenant_name)[0]
            if max_quota:
                quota = get_max_quota()
                id_membership.quota = quota
                id_membership.save
            return id_membership.identity
        except (IndexError, ProviderMembership.DoesNotExist):
            #Provider Membership
            p_membership = ProviderMembership.objects.get_or_create(
                provider=self.openstack_prov, member=group)[0]

            #Identity Membership
            identity = Identity.objects.get_or_create(
                created_by=user, provider=self.openstack_prov)[0]

            Credential.objects.get_or_create(
                identity=identity, key='key', value=username)[0]
            Credential.objects.get_or_create(
                identity=identity, key='secret', value=password)[0]
            Credential.objects.get_or_create(
                identity=identity, key='ex_tenant_name', value=tenant_name)[0]

            if max_quota:
                quota = get_max_quota()
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

    def hashpass(self, username):
        return sha1(username).hexdigest()
    def get_tenant_name_for(self, username):
        """
        This should always map tenant to user
        For now, they are identical..
        """
        return username

    def get_tenant(self, tenant):
        return self.user_manager.get_tenant(tenant)

    def list_tenants(self):
        return self.user_manager.list_tenants()

    def get_user(self, user):
        return self.user_manager.get_user(user)

    def list_users(self):
        return self.user_manager.list_users()

    def list_usergroup_names(self):
        usernames = []
        for (user,tenant) in self.list_usergroups():
                usernames.append(user.name)
        return usernames

    def list_usergroups(self):
        users = self.list_users()
        groups = self.list_tenants()
        usergroups = []
        for group in groups:
            for user in users:
                if user.name in group.name and\
                settings.OPENSTACK_ADMIN_KEY not in user.name:
                    usergroups.append((user,group))
                    break
        return usergroups
