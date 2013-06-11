"""
UserManager:
  Remote Openstack  Admin controls..
"""
from hashlib import sha1

from django.contrib.auth.models import User
from django.db.models import Max

from novaclient.v1_1 import client as nova_client
from novaclient.exceptions import OverLimit

from threepio import logger

from atmosphere import settings

from core.models.identity import Identity
from core.models.group import Group, IdentityMembership, ProviderMembership
from core.models.provider import Provider
from core.models.credential import Credential
from core.models.quota import Quota

from service.drivers.openstackUserManager import UserManager
from service.drivers.openstackImageManager import ImageManager
from service.drivers.openstackNetworkManager import NetworkManager
from service.drivers.common import _connect_to_glance, _connect_to_nova,\
                                   _connect_to_keystone


class AccountDriver():
    user_manager = None
    image_manager = None
    network_manager = None
    openstack_prov = None

    def __init__(self, *args, **kwargs):
        self.user_manager = UserManager(**settings.OPENSTACK_ARGS)
        self.image_manager = ImageManager(**settings.OPENSTACK_ARGS)
        network_args = settings.OPENSTACK_NETWORK_ARGS.copy()
        network_args.update(settings.OPENSTACK_ARGS)
        self.network_manager = NetworkManager(**network_args)
        self.openstack_prov = Provider.objects.get(location='OPENSTACK')

    def get_openstack_clients(self, username, password=None, tenant_name=None):
        if not tenant_name:
            tenant_name = self.get_project_name_for(username)
        if not password:
            password = self.hashpass(tenant_name)
        user_creds = {
            'auth_url':self.user_manager.nova.client.auth_url,
            'region_name':self.user_manager.nova.client.region_name,
            'username':username,
            'password':password,
            'tenant_name':tenant_name
        }
        quantum = self.network_manager.new_connection(**user_creds)
        keystone, nova, glance = self.image_manager.new_connection(**user_creds)
        return {
            'glance':glance, 
            'keystone':keystone, 
            'nova':nova, 
            'quantum':quantum
            }

    def create_account(self, username, admin_role=False, max_quota=False):
        """
        Create (And Update 'latest changes') to an account

        """
        finished = False
        # Special case for admin.. Use the Openstack admin identity..
        if username == 'admin':
            ident = self.create_openstack_identity(
                settings.OPENSTACK_ADMIN_KEY,
                settings.OPENSTACK_ADMIN_SECRET,
                settings.OPENSTACK_ADMIN_TENANT)
            return ident
        #Attempt account creation
        while not finished:
            try:
                password = self.hashpass(username)
                # Retrieve user, or create user & project
                user = self.get_or_create_user(username, password, True, admin_role)
                logger.debug(user)
                project = self.get_project(username)
                logger.debug(project)
                roles = user.list_roles(project)
                logger.debug(roles)
                if not roles:
                    self.user_manager.add_project_member(username,
                                                           username,
                                                           admin_role)
                self.user_manager.build_security_group(user.name,
                        self.hashpass(user.name), project.name)

                finished = True

            except OverLimit:
                print 'Requests are rate limited. Pausing for one minute.'
                time.sleep(60)  # Wait one minute
        ident = self.create_openstack_identity(username,
                                               password,
                                               project_name=username, max_quota=max_quota)
        return ident

    def create_openstack_identity(self, username, password, project_name, max_quota=False):
        #Get the usergroup
        (user, group) = self.create_usergroup(username)
        try:
            id_membership = IdentityMembership.objects.filter(
                identity__provider=self.openstack_prov,
                member__name=username,
                identity__credential__value__in=[
                    username, password, project_name]).distinct()[0]
            Credential.objects.get_or_create(
                identity=id_membership.identity,
                key='ex_project_name', value=project_name)[0]
            if max_quota:
                quota = self.get_max_quota()
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
                identity=identity, key='ex_tenant_name', value=project_name)[0]

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

            #Save the user (Calls a hook to update selected identity)
            id_membership.identity.created_by.save()

            #Return the identity
            return id_membership.identity

    def rebuild_project_network(self, username, project_name):
        self.network_manager.delete_project_network(username, project_name)
        self.network_manager.create_project_network(
            username,
            self.hashpass(username),
            project_name,
            **settings.OPENSTACK_NETWORK_ARGS)
        return True

    # Useful methods called from above..
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
            (project, user, role) = self.user_manager.add_usergroup(username,
                                                                  password,
                                                                  True,
                                                                  admin)
        else:
            user = self.user_manager.add_user(username, password)
            project = self.user_manager.get_project(username)
        #TODO: Instead, return user.get_user match, or call it if you have to..
        return user

    def delete_user(self, username, usergroup=True, admin=False):
        project = self.user_manager.get_project(username)
        if project:
            self.network_manager.delete_project_network(username, project.name)
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

    def get_max_quota(self):
        max_quota_by_cpu = Quota.objects.all().aggregate(Max('cpu')
                                                           )['cpu__max']
        quota = Quota.objects.filter(cpu=max_quota_by_cpu)
        return quota[0]

    def hashpass(self, username):
        return sha1(username).hexdigest()
    def get_project_name_for(self, username):
        """
        This should always map project to user
        For now, they are identical..
        """
        return username

    def get_project(self, project):
        return self.user_manager.get_project(project)

    def list_projects(self):
        return self.user_manager.list_projects()

    def get_user(self, user):
        return self.user_manager.get_user(user)

    def list_users(self):
        return self.user_manager.list_users()

    def list_usergroup_names(self):
        usernames = []
        for (user,project) in self.list_usergroups():
                usernames.append(user.name)
        return usernames

    def list_usergroups(self):
        users = self.list_users()
        groups = self.list_projects()
        usergroups = []
        for group in groups:
            for user in users:
                if user.name in group.name and\
                settings.OPENSTACK_ADMIN_KEY not in user.name:
                    usergroups.append((user,group))
                    break
        return usergroups
