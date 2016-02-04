"""
UserManager:
  Remote Openstack  Admin controls..
"""
import time
from hashlib import sha1
from urlparse import urlparse

from django.db.models import Max

from novaclient.v2 import client as nova_client
from novaclient.exceptions import OverLimit
from neutronclient.common.exceptions import NeutronClientException
from requests.exceptions import ConnectionError

from threepio import logger
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.openstack_user import UserManager
from chromogenic.drivers.openstack import ImageManager

from atmosphere import settings

from core.models import AtmosphereUser as User
from core.ldap import get_uid_number
from core.models.identity import Identity

from service.accounts.base import CachedAccountDriver


def get_random_uid(userid):
    """
    Given a string (Username) return a value < MAX_SUBNET
    """
    MAX_SUBNET = 4064
    return int(random.uniform(1, MAX_SUBNET))


class AccountDriver(CachedAccountDriver):
    user_manager = None
    image_manager = None
    network_manager = None
    core_provider = None

    MASTER_RULES_LIST = [
        ("ICMP", 0, 255),
        # FTP Access
        ("UDP", 20, 20),  # FTP data transfer
        ("TCP", 20, 21),  # FTP control
        # SSH & Telnet Access
        ("TCP", 22, 23),
        ("UDP", 22, 23),
        # SMTP Mail
        # HTTP Access
        ("TCP", 80, 80),
        # POP Mail
        # SFTP Access
        ("TCP", 115, 115),
        # SQL Access
        # IMAP Access
        # SNMP Access
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
        # SKIP PORT 4200.. See Below
        ("TCP", 4201, 65535),
        ("UDP", 4201, 65535),
        # Poke hole in 4200 for iPlant VMs proxy-access only (Shellinabox)
        ("TCP", 4200, 4200, "128.196.0.0/16"),
        ("UDP", 4200, 4200, "128.196.0.0/16"),
        ("TCP", 4200, 4200, "150.135.0.0/16"),
        ("UDP", 4200, 4200, "150.135.0.0/16"),

    ]

    def clear_cache(self):
        self.admin_driver.provider.machineCls.invalidate_provider_cache(
                self.admin_driver.provider)
        return self.admin_driver

    def _init_by_provider(self, provider, *args, **kwargs):
        from service.driver import get_esh_driver

        self.core_provider = provider

        provider_creds = provider.get_credentials()
        self.provider_creds = provider_creds
        admin_identity = provider.admin
        admin_creds = admin_identity.get_credentials()
        self.admin_driver = get_esh_driver(admin_identity)
        admin_creds = self._libcloud_to_openstack(admin_creds)
        all_creds = {'location': provider.get_location()}
        all_creds.update(admin_creds)
        all_creds.update(provider_creds)
        return all_creds

    def __init__(self, provider=None, *args, **kwargs):
        super(AccountDriver, self).__init__()
        if provider:
            all_creds = self._init_by_provider(provider, *args, **kwargs)
        else:
            all_creds = kwargs
        if 'location' in all_creds:
            self.namespace = "Atmosphere_OpenStack:%s" % all_creds['location']
        else:
            logger.info("Using default namespace.. Could cause conflicts if "
                        "switching between providers. To avoid ambiguity, "
                        "provide the kwarg: location='provider_prefix'")
        # Build credentials for each manager
        self.user_creds = self._build_user_creds(all_creds)
        self.image_creds = self._build_image_creds(all_creds)
        self.net_creds = self._build_network_creds(all_creds)

        # Initialize managers with respective credentials
        self.user_manager = UserManager(**self.user_creds)
        self.image_manager = ImageManager(**self.image_creds)
        self.network_manager = NetworkManager(**self.net_creds)

    def create_account(self, username, password=None, project_name=None,
                       role_name=None, quota=None, max_quota=False):
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
                                     quota=quota,
                                     max_quota=max_quota)
        return ident

    def build_account(self, username, password,
                      project_name=None, role_name=None, max_quota=False):
        finished = False

        # Attempt account creation
        while not finished:
            try:
                if not password:
                    password = self.hashpass(username)
                if not project_name:
                    project_name = username
                # 1. Create Project: should exist before creating user
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
                # TODO: providercredential initialization of
                #  "default_admin_role"
                self.user_manager.include_admin(project_name)

                # 3.2 Check the user has been given an appropriate role
                if not role_name:
                    role_name = "_member_"
                self.user_manager.add_project_membership(
                    project_name, username, role_name)

                # 4. Create a security group -- SUSPENDED.. Will occur on
                # instance launch instead.
                # self.init_security_group(user, password, project,
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
        # Change the description of the security group to match the project
        # name
        try:
            # Create the default security group
            nova = self.user_manager.build_nova(username, password,
                                                project_name)
            sec_groups = nova.security_groups.list()
            if not sec_groups:
                nova.security_group.create("default", project_name)
            self.network_manager.rename_security_group(project)
        except ConnectionError as ce:
            logger.exception(
                "Failed to establish connection."
                " Security group creation FAILED")
            return None
        except NeutronClientException as nce:
            if nce.status_code != 404:
                logger.exception("Encountered unknown exception while renaming"
                                 " the security group")
            return None

        # Start creating security group
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
        # 1. Remove non-credential information from the dict
        for key in credential_dict.keys():
            if key not in creds:
                credential_dict.pop(key)
        # 2. Check the dict has all the required credentials
        for c in creds:
            if not hasattr(credential_dict, c):
                missing_creds.append(c)
        return missing_creds

    def create_identity(self, username, password, project_name,
                        quota=None, max_quota=False, account_admin=False):

        if not self.core_provider:
            raise Exception("AccountDriver not initialized by provider, "
                            "cannot create identity")
        identity = Identity.create_identity(
            username, self.core_provider.location,
            quota=quota,
            # Flags..
            max_quota=max_quota, account_admin=account_admin,
            # Pass in credentials with cred_ namespace
            cred_key=username, cred_secret=password,
            cred_ex_tenant_name=project_name,
            cred_ex_project_name=project_name)

        # Return the identity
        return identity

    def rebuild_project_network(self, username, project_name,
                                dns_nameservers=[]):
        self.network_manager.delete_project_network(username, project_name)
        net_args = self._base_network_creds()
        self.network_manager.create_project_network(
            username,
            self.hashpass(username),
            project_name,
            get_unique_number=get_random_uid,
            dns_nameservers=dns_nameservers,
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
        # Core credentials need to be converted to openstack names
        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        project_name = identity_creds["tenant_name"]
        # Convert from libcloud names to openstack client names
        return self.network_manager.delete_project_network(
            username, project_name, remove_network=remove_network)

    def create_network(self, identity):
        # Core credentials need to be converted to openstack names
        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        password = identity_creds["password"]
        project_name = identity_creds["tenant_name"]
        dns_nameservers = [
            dns_server.ip_address for dns_server
            in identity.provider.dns_server_ips.order_by('order')]
        # Convert from libcloud names to openstack client names
        net_args = self._base_network_creds()
        return self.network_manager.create_project_network(
            username,
            password,
            project_name,
            get_unique_number=get_random_uid,
            dns_nameservers=dns_nameservers,
            **net_args)

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
        # TODO: Instead, return user.get_user match, or call it if you have
        # to..
        return user

    def delete_account(self, username, projectname):
        self.os_delete_account(username, projectname)
        Identity.delete_identity(username, self.core_provider.location)

    def os_delete_account(self, username, projectname):
        project = self.user_manager.get_project(projectname)

        # 1. Network cleanup
        if project:
            self.network_manager.delete_project_network(username, projectname)
            # 2. Role cleanup (Admin too)
            self.user_manager.delete_all_roles(username, projectname)
            adminuser = self.user_manager.keystone.username
            self.user_manager.delete_all_roles(adminuser, projectname)
            # 3. Project cleanup
            self.user_manager.delete_project(projectname)
        # 4. User cleanup
        user = self.user_manager.get_user(username)
        if user:
            self.user_manager.delete_user(username)
        return True

    def hashpass(self, username):
        # TODO: Must be better.
        return sha1(username).hexdigest()

    def get_project_name_for(self, username):
        """
        This should always map project to user
        For now, they are identical..
        """
        return username

    def _get_image(self, *args, **kwargs):
        return self.image_manager.get_image(*args, **kwargs)

    # For one-time caching
    def _list_all_images(self, *args, **kwargs):
        return self.image_manager.list_images(*args, **kwargs)

    def tenant_instances_map(
            self,
            status_list=[],
            match_all=False,
            include_empty=False):
        """
        Maps 'Tenant' objects to all the 'owned instances' as listed by the admin driver
        Optional fields:
        * status_list (list) - If provided, only include instance if it's status/tmp_status matches a value in the list.
        * match_all (bool) - If True, instances must match ALL words in the list.
        * include_empty (bool) - If True, include ALL tenants in the map.
        """
        all_projects = self.list_projects()
        all_instances = self.list_all_instances()
        if include_empty:
            project_map = {proj: [] for proj in all_projects}
        else:
            project_map = {}
        for instance in all_instances:
            try:
                # NOTE: will someday be 'projectId'
                tenant_id = instance.extra['tenantId']

                project = [p for p in all_projects if p.id == tenant_id][0]
            except (ValueError, KeyError):
                raise Exception(
                    "The implementaion for recovering a tenant id has changed. Update the code base above this line!")

            metadata = instance._node.extra.get('metadata', {})
            instance_status = instance.extra.get('status')
            task = instance.extra.get('task')
            tmp_status = metadata.get('tmp_status', '')
            if status_list:
                if match_all:
                    truth = all(
                        True if (
                            status_name and status_name in [
                                instance_status,
                                task,
                                tmp_status]) else False for status_name in status_list)
                else:
                    truth = any(
                        True if (
                            status_name and status_name in [
                                instance_status,
                                task,
                                tmp_status]) else False for status_name in status_list)
                if not truth:
                    logger.info(
                        "Found an instance:%s for tenant:%s but skipped because %s could be found in the list: (%s - %s - %s)" %
                        (instance.id,
                         project.name,
                         "none of the status_names" if not match_all else "not all of the status names",
                         instance_status,
                         task,
                         tmp_status))
                    continue
            instance_list = project_map.get(project, [])
            instance_list.append(instance)
            project_map[project] = instance_list
        return project_map

    def list_all_instances(self, **kwargs):
        return self.admin_driver.list_all_instances(**kwargs)

    def list_all_images(self, **kwargs):
        return self.image_manager.list_images(**kwargs)

    def get_project_by_id(self, project_id):
        return self.user_manager.get_project_by_id(project_id)

    def get_project(self, project_name):
        return self.user_manager.get_project(project_name)

    def _make_tenant_id_map(self):
        all_projects = self.list_projects()
        tenant_id_map = {project.id: project.name for project in all_projects}
        return tenant_id_map

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
        from rtwo.drivers.common import _connect_to_openstack_sdk
        # TODO: I could replace with identity.. but should I?
        # Build credentials for each manager
        all_creds = self._get_openstack_credentials(
            username, password, tenant_name)
        # Initialize managers with respective credentials
        user_creds = self._build_user_creds(all_creds)
        image_creds = self._build_image_creds(all_creds)
        net_creds = self._build_network_creds(all_creds)
        sdk_creds = self._build_sdk_creds(all_creds)

        openstack_sdk = _connect_to_openstack_sdk(**sdk_creds)
        neutron = self.network_manager.new_connection(**net_creds)
        keystone, nova, glance = self.image_manager._new_connection(
            **image_creds)
        return {
            "glance": glance,
            "keystone": keystone,
            "nova": nova,
            "neutron": neutron,
            "openstack_sdk": openstack_sdk,
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
            "admin_url": self.user_manager.keystone._management_url,
            "region_name": self.user_manager.nova.client.region_name,
            "username": username,
            "password": password,
            "tenant_name": tenant_name
        }
        return user_creds

    # Credential manipulaters
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
        if '/v2.0' not in net_args['auth_url']:
            net_args['auth_url'] += "/v2.0"
        return net_args

    def _build_network_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "NetworkManager" object
        NOTE: Expects auth_url to be '/v2.0'
        """
        net_args = credentials.copy()
        # Required:
        net_args.get("username")
        net_args.get("password")
        net_args.get("tenant_name")

        net_args.get("router_name")
        net_args.get("region_name")
        # Ignored:
        net_args["auth_url"] = net_args.pop("admin_url").replace("/tokens", "")
        net_args.pop("location", None)
        net_args.pop("ex_project_name", None)
        net_args.pop("ex_force_auth_version", None)
        if '/v2.0' not in net_args['auth_url']:
            net_args["auth_url"] += "/v2.0"
        return net_args

    def _build_image_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "UserManager" object
        NOTE: Expects auth_url to be '/v2.0/tokens'
        """
        img_args = credentials.copy()
        # Required:
        for required_arg in [
                "username",
                "password",
                "tenant_name",
                "auth_url",
                "region_name"]:
            if required_arg not in img_args or not img_args[required_arg]:
                raise ValueError(
                    "ImageManager is missing a Required Argument: %s" %
                    required_arg)
        img_args.pop("ex_force_auth_version",None)

        if 'v2.0/tokens' not in img_args['auth_url']:
            img_args["auth_url"] += "/v2.0/tokens"
        return img_args

    def _build_user_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "UserManager" object
        NOTE: Expects auth_url to be '/v2.0'
        """
        user_args = credentials.copy()
        # Required args:
        user_args.get("username")
        user_args.get("password")
        user_args.get("tenant_name")

        user_args["auth_url"] = user_args.get("auth_url")\
            .replace("/tokens", "")
        if 'v2' not in user_args['auth_url']:
            user_args["auth_url"] += "/v2.0/"
        user_args.get("region_name")
        # Removable args:
        user_args.pop("ex_force_auth_version", None)
        user_args.pop("admin_url", None)
        user_args.pop("location", None)
        user_args.pop("router_name", None)
        user_args.pop("ex_project_name", None)
        return user_args

    def _build_sdk_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build an "Openstack SDK" connection
        NOTE: Expects auth_url to be '/v2.0'
        """
        os_args = credentials.copy()
        # Required args:
        os_args.get("username")
        os_args.get("password")
        if 'tenant_name' in os_args and 'project_name' not in os_args:
            os_args['project_name'] = os_args.get("tenant_name")

        os_args["auth_url"] = os_args.get("auth_url")\
            .replace("/tokens", "")
        if 'v2' not in os_args['auth_url']:
            os_args["auth_url"] += "/v2.0/"
        os_args.get("region_name")
        # Removable args:
        os_args.pop("ex_force_auth_version", None)
        os_args.pop("admin_url", None)
        os_args.pop("location", None)
        os_args.pop("router_name", None)
        os_args.pop("ex_project_name", None)
        os_args.pop("ex_tenant_name", None)
        os_args.pop("tenant_name", None)
        return os_args
