"""
UserManager:
  Remote Openstack  Admin controls..
"""
from hashlib import sha1

from django.contrib.auth.models import User

from atmosphere import settings

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
            (tenant, user, role) = self.user_manager.addUsergroup(username,
                                                                  password,
                                                                  True,
                                                                  admin)
            logger.info("Creating network for %s" % username)
            self.network_manager.createTenantNetwork(username,
                                                     password,
                                                     tenant.name,
                                                     tenant.id)
        else:
            user = self.user_manager.addUser(username, password)
            tenant = self.user_manager.getTenant(username)
            self.network_manager.createTenantNetwork(username,
                                                     password,
                                                     tenant)
        #TODO: Instead, return user.get_user match, or call it if you have to..
        return user

    def delete_user(self, username, usergroup=True, admin=False):
        tenant = self.user_manager.getTenant(username)
        if tenant:
            self.network_manager.deleteTenantNetwork(username, tenant.name)
        if usergroup:
            deleted = self.user_manager.deleteUsergroup(username)
        else:
            deleted = self.user_manager.deleteUser(username)
        return deleted

    def create_usergroup(self, username):
        user = User.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=username)[0]

        user.groups.add(group)
        user.save()
        group.leaders.add(user)
        group.save()
        return (user, group)

    def create_openstack_identity(self, username, password, tenant_name):
        (user, group) = self.create_usergroup(username)
        try:
            id_member = IdentityMembership.objects.filter(
                identity__provider=self.openstack_prov,
                member__name=username,
                identity__credential__value__in=[
                    username, password, tenant_name]).distinct()[0]
            Credential.objects.get_or_create(
                identity=id_member.identity,
                key='ex_tenant_name', value=tenant_name)[0]
            return id_member.identity
        except (IndexError, ProviderMembership.DoesNotExist):
            #Add provider membership
            ProviderMembership.objects.get_or_create(
                provider=self.openstack_prov, member=group)[0]
            #Remove the user line when quota model is fixed
            default_quota = Quota().defaults()
            quota = Quota.objects.filter(cpu=default_quota['cpu'],
                                         memory=default_quota['memory'],
                                         storage=default_quota['storage'])[0]
            #Create the Identity
            identity = Identity.objects.get_or_create(
                created_by=user, provider=self.openstack_prov)[0]
            Credential.objects.get_or_create(
                identity=identity, key='key', value=username)[0]
            Credential.objects.get_or_create(
                identity=identity, key='secret', value=password)[0]
            Credential.objects.get_or_create(
                identity=identity, key='ex_tenant_name', value=tenant_name)[0]
            #Link it to the usergroup
            id_member = IdentityMembership.objects.get_or_create(
                identity=identity, member=group, quota=quota)[0]

            #Return the identity
            return id_member.identity

    def hashpass(self, username):
        return sha1(username).hexdigest()

    def get_tenant(self, tenant):
        return self.user_manager.getTenant(tenant)

    def list_tenants(self):
        return self.user_manager.listTenants()

    def get_user(self, user):
        return self.user_manager.getUser(user)

    def list_users(self):
        return self.user_manager.listUsers()

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
