"""
UserManager:
  Remote Openstack  Admin controls..
"""
import time
from hashlib import sha1
from urlparse import urlparse

from core.models import AtmosphereUser as User
from django.db.models import Max

from novaclient.v1_1 import client as nova_client
from novaclient.exceptions import OverLimit
from neutronclient.common.exceptions import NeutronClientException

from threepio import logger
from requests.exceptions import ConnectionError
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.openstack_user import UserManager

from core.ldap import get_uid_number
from core.models.identity import Identity

from chromogenic.drivers.openstack import ImageManager
from atmosphere import settings


class AccountDriver():
    user_manager = None
    image_manager = None
    network_manager = None
    core_provider = None

    MASTER_RULES_LIST = [
        ("ICMP", -1, 255),
        #FTP Access
        ("UDP", 20, 20),  # FTP data transfer
        ("TCP", 20, 21),  # FTP control
        #SSH & Telnet Access
        ("TCP", 22, 23),
        ("UDP", 22, 23),
        # SMTP Mail
        #("TCP", 25, 25),
        # HTTP Access
        ("TCP", 80, 80),
        # POP Mail
        #("TCP", 109, 110),
        # SFTP Access
        ("TCP", 115, 115),
        # SQL Access
        #("TCP", 118, 118),
        #("UDP", 118, 118),
        # IMAP Access
        #("TCP", 143, 143),
        # SNMP Access
        #("UDP", 161, 161),
        # LDAP Access
        ("TCP", 389, 389),
        ("UDP", 389, 389),
        # HTTPS Access
        ("TCP", 443, 443),
        # LDAPS Access
        ("TCP", 636, 636),
        ("UDP", 636, 636),
        # Open up >1024
        ("TCP", 1024, 4199),
        ("UDP", 1024, 4199),
        #SKIP PORT 4200.. See Below
        ("TCP", 4201, 65535),
        ("UDP", 4201, 65535),
        # Poke hole in 4200 for iPlant VMs proxy-access only (Shellinabox)
        ("TCP", 4200, 4200, "128.196.0.0/16"),
        ("UDP", 4200, 4200, "128.196.0.0/16"),
        ("TCP", 4200, 4200, "150.135.0.0/16"),
        ("UDP", 4200, 4200, "150.135.0.0/16"),

    ]

    def _init_by_provider(self, provider, *args, **kwargs):
        from api import get_esh_driver

        self.core_provider = provider

        provider_creds = provider.get_credentials()
        self.provider_creds = provider_creds
        admin_identity = provider.get_admin_identity()
        admin_creds = admin_identity.get_credentials()
        self.admin_driver = get_esh_driver(admin_identity)
        admin_creds = self._libcloud_to_openstack(admin_creds)
        all_creds = {}
        all_creds.update(admin_creds)
        all_creds.update(provider_creds)
        return all_creds

    def __init__(self, provider=None, *args, **kwargs):

        if provider:
            all_creds = self._init_by_provider(provider, *args, **kwargs)
        else:
            all_creds = kwargs

        # Build credentials for each manager
        self.user_creds = self._build_user_creds(all_creds)
        self.image_creds = self._build_image_creds(all_creds)
        self.net_creds = self._build_network_creds(all_creds)

        #Initialize managers with respective credentials
        self.user_manager = UserManager(**self.user_creds)
        self.image_manager = ImageManager(**self.image_creds)
        self.network_manager = NetworkManager(**self.net_creds)

    def create_account(self, username, password=None, project_name=None,
                       role_name=None, max_quota=False):
        """
        Create (And Update "latest changes") to an account

        """
        if not self.core_provider:
            raise Exception("AccountDriver not initialized by provider,"
                            " cannot create identity. For account creation use"
                            " build_account()")

        if username in self.core_provider.list_admin_names():
            return
        (username, password, project) = self.build_account(
            username, password, project_name, role_name, max_quota)
        ident = self.create_identity(username, password,
                                     project.name,
                                     max_quota=max_quota)
        return ident

    def build_account(self, username, password,
                      project_name=None, role_name=None, max_quota=False):
        finished = False

        #Attempt account creation
        while not finished:
            try:
                if not password:
                    password = self.hashpass(username)
                if not project_name:
                    project_name = username
                #1. Create Project: should exist before creating user
                project = self.user_manager.get_project(project_name)
                if not project:
                    project = self.user_manager.create_project(project_name)

                # 2. Create User (And add them to the project)
                user = self.get_user(username)
                if not user:
                    logger.info("Creating account: %s - %s - %s"
                                % (username, password, project))
                    user = self.user_manager.create_user(username, password,
                                                         project)
                # 3.1 Include the admin in the project
                #TODO: providercredential initialization of
                #  "default_admin_role"
                self.user_manager.include_admin(project_name)

                # 3.2 Check the user has been given an appropriate role
                if not role_name:
                    role_name = "_member_"
                self.user_manager.add_project_membership(
                    project_name, username, role_name)

                # 4. Create a security group -- SUSPENDED.. Will occur on
                # instance launch instead.
                #self.init_security_group(user, password, project,
                #                         project.name,
                #                         self.MASTER_RULES_LIST)

                # 5. Create a keypair to use when launching with atmosphere
                self.init_keypair(user.name, password, project.name)
                finished = True

            except ConnectionError:
                logger.exception("Connection reset by peer. "
                                 "Waiting for one minute.")
                time.sleep(60)  # Wait one minute
            except OverLimit:
                logger.exception("OverLimit on POST requests. "
                                 "Waiting for one minute.")
                time.sleep(60)  # Wait one minute
        return (username, password, project)

    def init_keypair(self, username, password, project_name):
        keyname = settings.ATMOSPHERE_KEYPAIR_NAME
        with open(settings.ATMOSPHERE_KEYPAIR_FILE, "r") as pub_key_file:
            public_key = pub_key_file.read()
        return self.get_or_create_keypair(username, password, project_name,
                                          keyname, public_key)

    def init_security_group(self, username, password, project_name,
                            security_group_name, rules_list):
        # 4.1. Update the account quota to hold a larger number of
        # roles than what is necessary
        user = self.user_manager.keystone.users.find(name=username)
        project = self.user_manager.keystone.tenants.find(name=project_name)
        nc = self.user_manager.nova
        rule_max = max(len(rules_list), 100)
        nc.quotas.update(project.id, security_group_rules=rule_max)
        #Change the description of the security group to match the project name
        try:
            #Create the default security group
            nova = self.user_manager.build_nova(username, password,
                                                project_name)
            sec_groups = nova.security_groups.list()
            if not sec_groups:
                nova.security_group.create("default", project_name)
            self.network_manager.rename_security_group(project)
        except NeutronClientException, nce:
            if nce.status_code != 404:
                logger.exception("Encountered unknown exception while renaming"
                                 " the security group")

        #Start creating security group
        return self.user_manager.build_security_group(
            user.name, password, project.name,
            security_group_name, rules_list)

    def add_rules_to_security_groups(self, core_identity_list,
                                     security_group_name, rules_list):
        for identity in core_identity_list:
            creds = self.parse_identity(identity)
            sec_group = self.user_manager.find_security_group(
                creds["username"], creds["password"], creds["tenant_name"],
                security_group_name)
            if not sec_group:
                raise Exception("No security gruop found matching name %s"
                                % security_group_name)
            self.user_manager.add_security_group_rules(
                creds["username"], creds["password"], creds["tenant_name"],
                security_group_name, rules_list)

    def get_or_create_keypair(self, username, password, project_name,
                              keyname, public_key):
        """
        keyname - Name of the keypair
        public_key - Contents of public key in OpenSSH format
        """
        clients = self.get_openstack_clients(username, password, project_name)
        nova = clients["nova"]
        keypairs = nova.keypairs.list()
        for kp in keypairs:
            if kp.name == keyname:
                if kp.public_key != public_key:
                    raise Exception(
                        "Mismatched public key found for keypair named: %s"
                        ". Expected: %s Original: %s"
                        % (keyname, public_key, kp.public_key))
                return (kp, False)
        return (self.create_keypair(
            username, password, project_name, keyname, public_key), True)

    def create_keypair(self, username, password,
                       project_name, keyname, public_key):
        """
        keyname - Name of the keypair
        public_key - Contents of public key in OpenSSH format
        """
        clients = self.get_openstack_clients(username, password, project_name)
        nova = clients["nova"]
        keypair = nova.keypairs.create(
            keyname,
            public_key=public_key)
        return keypair

    def rebuild_security_groups(self, core_identity, rules_list=None):
        creds = self.parse_identity(core_identity)
        if not rules_list:
            rules_list = self.MASTER_RULES_LIST
        return self.user_manager.build_security_group(
            creds["username"], creds["password"], creds["tenant_name"],
            creds["tenant_name"], rules_list, rebuild=True)

    def parse_identity(self, core_identity):
        identity_creds = self._libcloud_to_openstack(
            core_identity.get_credentials())
        return identity_creds

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

        if not self.core_provider:
            raise Exception("AccountDriver not initialized by provider, "
                            "cannot create identity")

        identity = Identity.create_identity(
            username, self.core_provider.location,
            #Flags..
            max_quota=max_quota, account_admin=account_admin,
            ##Pass in credentials with cred_ namespace
            cred_key=username, cred_secret=password,
            cred_ex_tenant_name=project_name,
            cred_ex_project_name=project_name)

        #Return the identity
        return identity

    def rebuild_project_network(self, username, project_name):
        self.network_manager.delete_project_network(username, project_name)
        net_args = self._base_network_creds()
        self.network_manager.create_project_network(
            username,
            self.hashpass(username),
            project_name,
            **net_args)
        return True

    def delete_security_group(self, identity):
        identity_creds = self.parse_identity(identity)
        project_name = identity_creds["tenant_name"]
        project = self.user_manager.keystone.tenants.find(name=project_name)
        sec_group_r = self.network_manager.neutron.list_security_groups(
            tenant_id=project.id)
        sec_groups = sec_group_r["security_groups"]
        for sec_group in sec_groups:
            self.network_manager.neutron.delete_security_group(sec_group["id"])
        return True

    def delete_network(self, identity, remove_network=True):
        #Core credentials need to be converted to openstack names
        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        #password = identity_creds["password"]
        project_name = identity_creds["tenant_name"]
        # Convert from libcloud names to openstack client names
        #net_args = self._base_network_creds()
        return self.network_manager.delete_project_network(
            username, project_name, remove_network=remove_network)

    def create_network(self, identity):
        #Core credentials need to be converted to openstack names
        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        password = identity_creds["password"]
        project_name = identity_creds["tenant_name"]
        # Convert from libcloud names to openstack client names
        net_args = self._base_network_creds()
        return self.network_manager.create_project_network(
            username, password, project_name,
            get_cidr=get_uid_number, **net_args)

    # Useful methods called from above..
    def get_or_create_user(self, username, password=None,
                           project=None, admin=False):
        user = self.get_user(username)
        if user:
            return user
        user = self.create_user(username, password, usergroup, admin)
        return user

    def create_user(self, username,
                    password=None, usergroup=True, admin=False):
        if not password:
            password = self.hashpass(username)
        if usergroup:
            (project, user, role) = self.user_manager.add_usergroup(
                username, password, True, admin)
        else:
            user = self.user_manager.add_user(username, password)
            project = self.user_manager.get_project(username)
        #TODO: Instead, return user.get_user match, or call it if you have to..
        return user

    def delete_account(self, username, projectname):
        self.os_delete_account(username, projectname)
        Identity.delete_identity(username, self.core_provider.location)

    def os_delete_account(self, username, projectname):
        project = self.user_manager.get_project(projectname)

        #1. Network cleanup
        if project:
            self.network_manager.delete_project_network(username, projectname)
            #2. Role cleanup (Admin too)
            self.user_manager.delete_all_roles(username, projectname)
            adminuser = self.user_manager.keystone.username
            self.user_manager.delete_all_roles(adminuser, projectname)
            #3. Project cleanup
            self.user_manager.delete_project(projectname)
        #4. User cleanup
        user = self.user_manager.get_user(username)
        if user:
            self.user_manager.delete_user(username)
        return True

    def hashpass(self, username):
        #TODO: Must be better.
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
        admin_usernames = self.core_provider.list_admin_names()
        for group in groups:
            for user in users:
                if user.name in admin_usernames:
                    continue
                if user.name in group.name:
                    usergroups.append((user, group))
                    break
        return usergroups

    def _get_horizon_url(self, tenant_id):
        parsed_url = urlparse(self.provider_creds["auth_url"])
        return "https://%s/horizon/auth/switch/%s/?next=/horizon/project/" %\
            (parsed_url.hostname, tenant_id)

    def get_openstack_clients(self, username, password=None, tenant_name=None):
        #TODO: I could replace with identity.. but should I?
        user_creds = self._get_openstack_credentials(
            username, password, tenant_name)
        neutron = self.network_manager.new_connection(**user_creds)
        keystone, nova, glance = self.image_manager._new_connection(
            **user_creds)
        return {
            "glance": glance,
            "keystone": keystone,
            "nova": nova,
            "neutron": neutron,
            "horizon": self._get_horizon_url(keystone.tenant_id)
            }

    def _get_openstack_credentials(self, username,
                                   password=None, tenant_name=None):
        if not tenant_name:
            tenant_name = self.get_project_name_for(username)
        if not password:
            password = self.hashpass(tenant_name)
        user_creds = {
            "auth_url": self.user_manager.nova.client.auth_url,
            "region_name": self.user_manager.nova.client.region_name,
            "username": username,
            "password": password,
            "tenant_name": tenant_name
        }
        return user_creds

    ## Credential manipulaters
    def _libcloud_to_openstack(self, credentials):
        credentials["username"] = credentials.pop("key")
        credentials["password"] = credentials.pop("secret")
        credentials["tenant_name"] = credentials.pop("ex_tenant_name")
        return credentials

    def _base_network_creds(self):
        """
        These credentials should be used when another user/pass/tenant
        combination will be used
        """
        net_args = self.provider_creds.copy()
        net_args["auth_url"] = net_args.pop("admin_url").replace("/tokens", "")
        return net_args

    def _build_network_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "NetworkManager" object
        """
        net_args = credentials.copy()
        #Required:
        net_args.get("username")
        net_args.get("password")
        net_args.get("tenant_name")

        net_args.get("router_name")
        net_args.get("region_name")
        #Ignored:
        net_args["auth_url"] = net_args.pop("admin_url").replace("/tokens", "")

        return net_args

    def _build_image_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "UserManager" object
        """
        img_args = credentials.copy()
        #Required:
        img_args.get("username")
        img_args.get("password")
        img_args.get("tenant_name")

        img_args["auth_url"] = img_args.get("auth_url").replace("/tokens", "")
        img_args.get("region_name")
        #Ignored:
        img_args.pop("admin_url", None)
        img_args.pop("router_name", None)
        img_args.pop("ex_project_name", None)

        return img_args

    def _build_user_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "UserManager" object
        """
        user_args = credentials.copy()
        #Required args:
        user_args.get("username")
        user_args.get("password")
        user_args.get("tenant_name")

        user_args["auth_url"] = user_args.get("auth_url")\
            .replace("/tokens", "")
        user_args.get("region_name")
        #Removable args:
        user_args.pop("admin_url", None)
        user_args.pop("router_name", None)
        user_args.pop("ex_project_name", None)
        return user_args
