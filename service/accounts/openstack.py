"""
UserManager:
  Remote Openstack  Admin controls..
"""
from hashlib import sha1
from urlparse import urlparse

from django.contrib.auth.models import User
from django.db.models import Max

from novaclient.v1_1 import client as nova_client
from novaclient.exceptions import OverLimit

from threepio import logger

from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.openstack_user import UserManager

from core.ldap import get_uid_number
from core.models.identity import Identity

from service.imaging.drivers.openstack import ImageManager

class AccountDriver():
    user_manager = None
    image_manager = None
    network_manager = None
    openstack_prov = None

    def _libcloud_to_openstack(self, credentials):
        credentials['username'] = credentials.pop('key')
        credentials['password'] = credentials.pop('secret')
        credentials['tenant_name'] = credentials.pop('ex_tenant_name')
        return credentials


    def __init__(self, provider, *args, **kwargs):
        admin_creds = provider.get_admin_identity().get_credentials()
        # Convert from libcloud names to openstack client names
        admin_creds = self._libcloud_to_openstack(admin_creds)
        self.admin_creds = admin_creds
        provider_creds = provider.get_credentials()
        self.provider_creds = provider_creds
        user_args = {}
        user_args.update(admin_creds)
        user_args.update(provider_creds)
        #These args are NOT required for user manager
        admin_url = user_args.pop('admin_url', None)
        router_name = user_args.pop('router_name', None)
        self.user_manager = UserManager(**user_args)
        self.image_manager = ImageManager(**user_args)
        # auth_url --> admin_url && router_name
        # required for initializing networkmanager
        user_args['router_name'] = router_name
        user_args['auth_url'] = admin_url
        self.network_manager = NetworkManager(**user_args)
        self.openstack_prov = provider

    def get_openstack_clients(self, username, password=None, tenant_name=None):
        user_creds = self._get_openstack_credentials(
                            username, password, tenant_name)
        neutron = self.network_manager.new_connection(**user_creds)
        keystone, nova, glance = self.image_manager.new_connection(**user_creds)
        return {
            'glance':glance, 
            'keystone':keystone, 
            'nova':nova, 
            'neutron':neutron,
            'horizon':self._get_horizon_url(keystone.tenant_id)
            }


    def _get_horizon_url(self, tenant_id):
        parsed_url = urlparse(self.provider_creds['auth_url'])
        return 'https://%s/horizon/auth/switch/%s/?next=/horizon/project/' %\
            (parsed_url.hostname, tenant_id)


    def create_account(self, username, admin_role=False, max_quota=False):
        """
        Create (And Update 'latest changes') to an account

        """
        finished = False
        #TODO: How will we handle this special case?
        # The first time we are running in all users, we will hit 'user with
        # non-standard password'. How will we know what the right credentials
        # are?

        if username in self.openstack_prov.list_admin_names():
            return

        #Attempt account creation
        while not finished:
            try:
                password = self.hashpass(username)
                # Retrieve user, or create user & project
                user = self.get_or_create_user(username, password,
                                               usergroup=True, admin=admin_role)
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
        ident = self.create_identity(username, password,
                                     project_name=username,
                                     max_quota=max_quota)
        return ident

    def clean_credentials(self, credential_dict):
        """
        This function cleans up a dictionary of credentials.
        After running this function:
        * Erroneous dictionary keys are removed
        * Missing credentials are listed
        """
        creds = ["username", "password", "project_name"]
        missing_creds = []
        #1. Remove non-credential information from the dict
        for key in credential_dict.keys():
            if key not in creds:
                credential_dict.pop(key)
        #2. Check the dict has all the required credentials
        for c in creds:
            if not hasattr(credential_dict, c):
                missing_creds.append(c)
        return missing_creds


    def create_identity(self, username, password, project_name,
            max_quota=False, account_admin=False):
        identity = Identity.create_identity(
                username, self.openstack_prov.location,
                #Flags..
                max_quota=max_quota, account_admin=account_admin,
                ##Pass in credentials with cred_ namespace
                cred_key=username, cred_secret=password,
                cred_ex_tenant_name=project_name,
                cred_ex_project_name=project_name)

        #Return the identity
        return identity

    def _get_net_args(self):
        net_args = self.provider_creds.copy()
        net_args['auth_url'] = net_args.pop('admin_url',None)
        return net_args

    def rebuild_project_network(self, username, project_name):
        self.network_manager.delete_project_network(username, project_name)
        net_args = self._get_net_args()
        self.network_manager.create_project_network(
            username,
            self.hashpass(username),
            project_name,
            **net_args)
        return True

    def create_network(self, identity):
        #Core credentials need to be converted to openstack names
        admin_creds = self._libcloud_to_openstack(
                identity.get_credentials())
        username = admin_creds['username']
        password = admin_creds['password']
        project_name = admin_creds['tenant_name']
        # Convert from libcloud names to openstack client names
        net_args = self._get_net_args()
        self.network_manager.create_project_network(
                username, password, project_name,
                get_cidr=get_uid_number, **net_args)



    # Useful methods called from above..
    def get_or_create_user(self, username, password=None,
                           usergroup=True, admin=False):
        user = self.get_user(username)
        if user:
            return user
        user = self.create_user(username, password, usergroup, admin)
        return user

    def create_user(self, username, password=None, usergroup=True, admin=False):
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
        return [user.name for (user, project) in self.list_usergroups()]

    def list_usergroups(self):
        """
        TODO: This function is AWFUL just scrap it.
        """
        users = self.list_users()
        groups = self.list_projects()
        usergroups = []
        admin_usernames = self.openstack_prov.list_admin_names()
        for group in groups:
            for user in users:
                if user.name in admin_usernames:
                    continue
                if user.name in group.name:
                    usergroups.append((user,group))
                    break
        return usergroups

    def _get_openstack_credentials(self, username, password=None, tenant_name=None):
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
        return user_creds

