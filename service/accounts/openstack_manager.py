"""
UserManager:
  Remote Openstack  Admin controls..
"""
import time
import string
from urlparse import urlparse

from django.db.models import Max

from django.db.models import ObjectDoesNotExist
from rtwo.exceptions import NovaOverLimit
from rtwo.exceptions import NeutronClientException, GlanceClientException
from requests.exceptions import ConnectionError
from hashlib import sha256

from threepio import logger
from rtwo.drivers.common import _connect_to_openstack_sdk
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.openstack_user import UserManager
from chromogenic.drivers.openstack import ImageManager

from atmosphere import settings

from core.models.identity import Identity

from service.accounts.base import BaseAccountDriver
from service.networking import get_topology_cls, ExternalRouter, ExternalNetwork, _get_unique_id

from atmosphere.settings.secrets import SECRET_SEED
from atmosphere.settings import DEFAULT_PASSWORD_UPDATE, DEFAULT_RULES


class AccountDriver(BaseAccountDriver):
    user_manager = None
    image_manager = None
    network_manager = None
    core_provider = None
    cloud_config = {}

    @classmethod
    def generate_openrc(cls, identity, filename=None):
        export_data = cls.export_identity(identity)
        str_builder = ""
        for key, val in export_data.iteritems():
            str_builder += "export %s=%s\n" % (key, val)
        if filename:
            with open(filename,'w') as the_file:
                the_file.write(str_builder)
        return str_builder

    @classmethod
    def export_identity(cls, identity):
        """
        Returns the dict required to generate an openrc.
        This can be used to verify cloud connectivity
        via external CLI tools.
        """
        all_creds = identity.get_all_credentials()
        tenant_name = all_creds.get('ex_project_name', "<PROJECT MISSING>")
        username = all_creds.get('key', "<USERNAME MISSING>")
        password = all_creds.get('secret',"<PASSWORD MISSING>")
        project_domain = all_creds.get('project_domain', 'default')
        user_domain = all_creds.get('user_domain', 'default')
        region_name = all_creds.get('region_name', 'RegionOne')
        keystone_auth_version = all_creds.get('ex_force_auth_version', '2.0_password').replace('/v2.0/tokens', '')
        is_v2 = '2' in keystone_auth_version
        is_v3 = '3' in keystone_auth_version
        version_prefix = "/v2.0" if is_v2 else '/v3'
        #auth_url = all_creds.get('auth_url', '<AUTH URL MISSING>') + version_prefix
        admin_url = all_creds.get('admin_url', '<ADMIN URL MISSING>').replace('/v2.0/tokens', '') + version_prefix
        export_data = {
            "OS_REGION_NAME": region_name,
            "OS_AUTH_URL": admin_url,
            "OS_USERNAME": username,
            "OS_PASSWORD": password,
            "OS_TENANT_NAME": tenant_name,
        }
        if is_v3:
            export_data.update({
                "OS_IDENTITY_API_VERSION": 3,
                "OS_PROJECT_NAME": tenant_name,
                "OS_PROJECT_DOMAIN_NAME": project_domain,
                "OS_USER_DOMAIN_NAME": user_domain,
            })
        return export_data

    def clear_cache(self):
        self.admin_driver.provider.machineCls.invalidate_provider_cache(
                self.admin_driver.provider)
        return self.admin_driver

    def _init_by_provider(self, provider, *args, **kwargs):
        from service.driver import get_esh_driver

        self.core_provider = provider

        provider_creds = provider.get_credentials()
        self.cloud_config = provider.cloud_config
        self.provider_creds = provider_creds
        if not provider.admin:
            raise Exception("Cannot create an account driver yet - A provider admin account has not been created")
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
        if 'cloud_config' in all_creds:
            self.cloud_config = all_creds['cloud_config']
        if not self.cloud_config:
            self.cloud_config = {}

        if 'location' in all_creds:
            self.namespace = "Atmosphere_OpenStack:%s" % all_creds['location']
        else:
            logger.info("Using default namespace.. Could cause conflicts if "
                        "switching between providers. To avoid ambiguity, "
                        "provide the kwarg: location='provider_prefix'")
        # Build credentials for each manager
        self.credentials = all_creds

        ex_auth_version = all_creds.get("ex_force_auth_version", '2.0_password')
        if ex_auth_version.startswith('2'):
            self.identity_version = 2
        elif ex_auth_version.startswith('3'):
            self.identity_version = 3
        else:
            raise Exception("Could not determine identity_version of %s"
                            % ex_auth_version)

        user_creds = self._build_user_creds(all_creds)
        image_creds = self._build_image_creds(all_creds)
        net_creds = self._build_network_creds(all_creds)
        sdk_creds = self._build_sdk_creds(all_creds)

        # Initialize managers with respective credentials
        self.user_manager = UserManager(**user_creds)
        self.image_manager = ImageManager(**image_creds)
        self.network_manager = NetworkManager(**net_creds)
        self.openstack_sdk = _connect_to_openstack_sdk(**sdk_creds)

    def get_config(self, section, config_key, default_value):
        try:
            value = self.cloud_config[section][config_key]
        except (KeyError, TypeError):
            logger.error("Cloud config ['%s']['%s'] is missing -- using default value (%s)" % (section, config_key, default_value))
            value = default_value
        return value

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
                      project_name=None, role_name=None, max_quota=False, domain_name='default'):
        finished = False
        # Attempt account creation
        while not finished:
            try:
                if not password:
                    password = self.hashpass(username)
                if not project_name:
                    project_name = username
                # 1. Create Project: should exist before creating user
                project_kwargs = {}
                if self.identity_version > 2:
                    project_kwargs.update({'domain_id': domain_name})
                project = self.user_manager.get_project(project_name, **project_kwargs)
                if not project:
                    if self.identity_version > 2:
                        project_kwargs = {'domain': domain_name}
                    project = self.user_manager.create_project(project_name, **project_kwargs)
                # 2. Create User (And add them to the project)
                user = self.get_user(username)
                if not user:
                    logger.info("Creating account: %s - %s - %s"
                                % (username, password, project))
                    user_kwargs = {}
                    if self.identity_version > 2:
                        user_kwargs.update({'domain': domain_name})
                    user = self.user_manager.create_user(username, password,
                                                         project, **user_kwargs)
                # 3.1 Include the admin in the project
                # TODO: providercredential initialization of
                #  "default_admin_role"
                self.user_manager.include_admin(project_name)

                # 3.2 Check the user has been given an appropriate role
                if not role_name:
                    role_name = self.get_config('user', 'user_role_name', settings.DEFAULT_KEYSTONE_ROLE)
                try:
                    self.user_manager.add_project_membership(
                        project_name, username, role_name, domain_name)
                except:
                    raise Exception("Could not add role %s to user %s for project %s -- Check 'user_role_name'"
                                    % (role_name, username, project_name))

                # 4. Create a keypair to use when launching with atmosphere
                self.init_keypair(user.name, password, project.name)
                finished = True

            except ConnectionError:
                logger.exception("Connection reset by peer. "
                                 "Waiting for one minute.")
                time.sleep(60)  # Wait one minute
            except NovaOverLimit:
                logger.exception("OverLimit on POST requests. "
                                 "Waiting for one minute.")
                time.sleep(60)  # Wait one minute
        return (username, password, project)

    def change_password(self, identity, new_password, old_password=None):
        try:
            self.update_password_for(identity, new_password)
            self.update_password_credential(identity, new_password)
            return True
        except Exception:
            logger.exception("Could not change password")
            return False

    def update_password_credential(self, core_identity, new_password):
        """

        """
        try:
            password_cred = core_identity.credential_set.get(key='secret')
            password_cred.value = new_password
            password_cred.save()
        except ObjectDoesNotExist:
            raise Exception(
                "The 'key' for a secret has changed! "
                "Ask a programmer for help!")

    def update_password_for(self, identity, new_password, strategy=None):
        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        return self.update_password_for_user(username, new_password, strategy=strategy)

    def update_password_for_user(self, username, new_password, strategy=None):

        if not strategy:
            strategy = DEFAULT_PASSWORD_UPDATE

        if not strategy\
                or strategy == 'keystone_password_update':
            return self.keystone_password_update(username, new_password)
        if strategy in ['openstack_sdk_password_update',
                        'openstack_password_update']:
            return self.openstack_sdk_password_update(username, new_password)
        else:
            raise ValueError(
                "Invalid 'Update Password' strategy: %s"
                % strategy)

    def keystone_password_update(self, username, new_password):
        keystone = self.user_manager.keystone
        user = keystone.users.find(name=username)
        return keystone.users.update_password(user, new_password)

    def openstack_sdk_password_update(self, username, new_password):
        user_id = self.get_user(username).id
        return self.openstack_sdk.identity.update_user(user_id, password=new_password)

    def init_keypair(self, username, password, project_name):
        keyname = settings.ATMOSPHERE_KEYPAIR_NAME
        with open(settings.ATMOSPHERE_KEYPAIR_FILE, "r") as pub_key_file:
            public_key = pub_key_file.read()
        return self.get_or_create_keypair(username, password, project_name,
                                          keyname, public_key)

    def init_security_group(self, core_identity, security_group_name=None):
        # 4.1. Update the account quota to hold a larger number of
        # roles than what is necessary
        # user = user_matches[0]
        # -- User:Keystone rev.
        rules_list = self.get_config('network', 'default_security_rules', DEFAULT_RULES)
        identity_creds = self.parse_identity(core_identity)
        username = identity_creds["username"]
        password = identity_creds["password"]
        project_name = identity_creds["tenant_name"]
        kwargs = {}
        if self.identity_version > 2:
            kwargs.update({'domain': 'default'})
        user_matches = [u for u in self.user_manager.keystone.users.list(**kwargs) if u.name == username]
        if not user_matches or len(user_matches) > 1:
            raise Exception("User maps to *MORE* than one account on openstack default domain! Ask a programmer for help here!")
        user = user_matches[0]
        kwargs = {}
        if self.identity_version > 2:
            kwargs.update({'domain_id': 'default'})
        project = self.user_manager.keystone_projects().find(name=project_name, **kwargs)
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
            self.network_manager.rename_security_group(
                project, security_group_name=security_group_name)
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
        if self.identity_version == 2:
            nova = clients["nova"]
            keypairs = nova.keypairs.list()
        else:
            osdk = clients["openstack_sdk"]
            keypairs = [kp for kp in osdk.compute.keypairs()]
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
        if self.identity_version == 2:
            nova = clients["nova"]
            keypair = nova.keypairs.create(
                    keyname,
                    public_key=public_key)
        else:
            osdk = clients["openstack_sdk"]
            keypair = osdk.compute.create_keypair(
                name=keyname,
                public_key=public_key)
        return keypair

    def shared_images_for(self, image_id):
        acct_driver = None

        shared_with = self.image_manager.shared_images_for(
            image_id=image_id)

	if getattr(settings, "REPLICATION_PROVIDER_LOCATION"):
            from core.models import Provider
            from service.driver import get_account_driver
            provider = Provider.objects.get(location=settings.REPLICATION_PROVIDER_LOCATION)
            acct_driver = get_account_driver(provider)
            if not acct_driver:
                raise Exception("Cannot create account_driver for %s" % provider)
        else:
            acct_driver = self

        projects = [acct_driver.get_project_by_id(member.member_id)
                    for member in shared_with]
        return projects

    def share_image_with_project(self, glance_image, project_name):
        try:
            self.image_manager.share_image(glance_image, project_name)
            self.accept_shared_image(glance_image, project_name)
            logger.info("Added Cloud Access: %s-%s"
                        % (glance_image, project_name))
        except GlanceClientException as gce:
            message = gce.details
            if 'is duplicated for image' not in message\
                    and 'is already associated with image' not in message:
                raise

    def accept_shared_image(self, glance_image, project_name):
        """
        This is only required when sharing using 'the v2 api' on glance.
        """
        # FIXME: Abusing the 'project_name' == 'username' mapping
        clients = self.get_openstack_clients(project_name)
        project = self.user_manager.get_project(project_name)
        glance = clients["glance"]
        glance.image_members.update(
            glance_image.id,
            project.id,
            'accepted')

        

    def rebuild_security_groups(self, core_identity, rules_list=None):
        creds = self.parse_identity(core_identity)
        if not rules_list:
            rules_list = self.get_config('network', 'default_security_rules', DEFAULT_RULES)
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
            get_unique_number=_get_unique_id,
            dns_nameservers=dns_nameservers,
            **net_args)
        return True

    def delete_security_group(self, identity):
        identity_creds = self.parse_identity(identity)
        project_name = identity_creds["tenant_name"]
        project = self.user_manager.keystone.projects.find(name=project_name)
        sec_group_r = self.network_manager.neutron.list_security_groups(
            tenant_id=project.id)
        sec_groups = sec_group_r["security_groups"]
        for sec_group in sec_groups:
            self.network_manager.neutron.delete_security_group(sec_group["id"])
        return True

    def initialize_network_strategy(self, topology_name, identity, network_driver, neutron):
        """
        Select a network topology and initialize it with the identity/provider specific information required.
        """
        # Select Cls
        if not topology_name:
            logger.info("Selecting default topology - ExternalRouter")
            NetworkTopologyStrategyCls = ExternalRouter
        else:
            NetworkTopologyStrategyCls = get_topology_cls(topology_name)

        try:
            network_strategy = NetworkTopologyStrategyCls(identity, network_driver, neutron)
            # validate should raise exception if mis-configured.
            network_strategy.validate(identity)
        except:
            logger.exception(
                "Error initializing Network Topology - %s + %s " %
                (NetworkTopologyStrategyCls, identity))
            raise
        return network_strategy

    def dns_nameservers_for(self, identity):
        dns_nameservers = [
            dns_server.ip_address for dns_server
            in identity.provider.dns_server_ips.order_by('order')
        ]
        return dns_nameservers

    def delete_user_network(self, identity, options={}):
        """
        1. Look at the provider for network topology hints
        2. If no network topology exists, use the "Default network" settings.
        3. Delete network based on topology
        """

        identity_creds = self.parse_identity(identity)
        project_name = identity_creds["tenant_name"]
        neutron = self.get_openstack_client(identity, 'neutron')
        topology_name = self.get_config('network', 'topology', None)
        if not topology_name:
            logger.error(
                "Network topology not selected -- "
                "Will attempt to use the last known default: ExternalRouter.")
        network_strategy = self.initialize_network_strategy(
            topology_name, identity, self.network_manager, neutron)
        skip_network = options.get("skip_network", False)
        return network_strategy.delete(skip_network=skip_network)

    def find_user_network(self, identity):
        """
        1. Look at the provider for network topology hints
        2. If no network topology exists, use the "Default network" settings.
        3. Create network based on topology
        """
        # Prepare args

        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        project_name = identity_creds["tenant_name"]
        neutron = self.get_openstack_client(identity, 'neutron')
        dns_nameservers = self.dns_nameservers_for(identity)
        network = self.network_manager.find_network(
            "%s-net" % project_name)
        # Use `network.name` from here
        subnet = self.network_manager.find_subnet(
            "%s-subnet" % project_name)
        router = self.network_manager.find_router(
            "%s-router" % project_name)
        # gateway = self.network_manager.find_router_gateway(
        #     "%s-router" % project_name)
        interface = None
        if router and subnet:
            interface = self.network_manager.find_router_interface(
            router[0], subnet[0])
        network_resources = {
            'network': network,
            'subnet': subnet,
            'router': router,
            #'gateway': gateway,
            'interface': interface,
        }
        return network_resources

    def create_user_network(self, identity):
        """
        1. Look at the provider for network topology hints
        2. If no network topology exists, use the "Default network" settings.
        3. Create network based on topology
        """
        # Prepare args

        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        # NOTE: While 'prefixing' would be nice, how we transition to this
        #       when we already have "non-prefixed" resources might be tough.
        #       to avoid conflicts with production boxes, we will not implement
        #       the prefixing portion now.
        #prefix_name = "atmo_%s" % (identity_creds["tenant_name"],)
        prefix_name = "%s" % (identity_creds["tenant_name"],)
        neutron = self.get_openstack_client(identity, 'neutron')
        dns_nameservers = self.dns_nameservers_for(identity)
        topology_name = self.get_config('network', 'topology', None)
        if not topology_name:
            logger.error(
                "Network topology not selected -- "
                "Will attempt to use the last known default: ExternalRouter.")
        network_strategy = self.initialize_network_strategy(
            topology_name, identity, self.network_manager, neutron)
        network_resources = network_strategy.create(
            username=username, dns_nameservers=dns_nameservers)
        network_strategy.post_create_hook(network_resources)
        return network_resources

    # Useful methods called from above..
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
        """
        Create a unique password using 'username'
        """
        #FIXME: Remove these lines when crypt_hashpass is no longer used.
        strategy = self.get_config('user', 'strategy', '')
        cloud_pass = self.get_config('user', 'secret', '')

        if strategy == 'crypt':
            return self.crypt_hashpass(username)
        elif strategy == 'sha_v1':
            return self.sha_v1_hashpass(username, cloud_pass)
        else:
            return self.sha_v2_hashpass(username, cloud_pass)

    def sha_v2_hashpass(self, username, cloud_pass):
        if not cloud_pass or len(cloud_pass) < 32:
            raise ValueError("Cloud config ['user']['secret'] is required and " +
                    "must be of length 32 or more")

        if not username:
            raise ValueError("Missing username, cannot create hash")
        return sha256(username + cloud_pass).hexdigest()

    def sha_v1_hashpass(self, username, cloud_pass):
        if not cloud_pass:
            raise ValueError("Cloud config ['user']['secret'] is required")

        if not username:
            raise ValueError("Missing username, cannot create hash")
        return sha256(cloud_pass + username).hexdigest()

    def crypt_hashpass(self, username):
        """
        Create a unique password using 'username'
        """
        import crypt
        cloud_pass = self.get_config('user', 'secret', None)
        secret_salt = str(cloud_pass).translate(None, string.punctuation)
        password = crypt.crypt(username, secret_salt)
        return password

    def get_project_name_for(self, username):
        """
        This should always map project to user
        For now, they are identical..
        TODO: Make this intelligent. use keystone.
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

    def list_all_snapshots(self, **kwargs):
        return [img for img in self.list_all_images(**kwargs) if 'snapshot' in img.get('image_type','image').lower()]

    def get_project_by_id(self, project_id):
        return self.user_manager.get_project_by_id(project_id)

    def get_project(self, project_name, **kwargs):
        if self.identity_version > 2:
            kwargs = self._parse_domain_kwargs(kwargs)
        return self.user_manager.get_project(project_name, **kwargs)

    def _make_tenant_id_map(self):
        all_projects = self.list_projects()
        tenant_id_map = {project.id: project.name for project in all_projects}
        return tenant_id_map

    def create_trust(
            self,
            trustee_project_name, trustee_username, trustee_domain_name,
            trustor_project_name, trustor_username, trustor_domain_name,
            roles=[], impersonation=True):
        """
        Trustee == Consumer
        Trustor == Resource Owner
        Given the *names* of projects, users, and domains
        gather all required information for a Trust-Create
        create a new trust object

        NOTE: we set impersonation to True
        -- it has a 'normal default' of False!
        """
        default_roles = [{"name": "admin"}]
        trustor_domain = self.openstack_sdk.identity.find_domain(
            trustor_domain_name)
        if not trustor_domain:
            raise ValueError("Could not find trustor domain named %s"
                             % trustor_domain_name)

        trustee_domain = self.openstack_sdk.identity.find_domain(
            trustee_domain_name)
        if not trustee_domain:
            raise ValueError("Could not find trustee domain named %s"
                             % trustee_domain_name)

        trustee_user = self.get_user(
            trustee_username, domain_id=trustee_domain.id)
        # trustee_project = self.get_project(
        #    trustee_username, domain_name=trustee_domain.id)
        trustor_user = self.get_user(
            trustor_username, domain_id=trustor_domain.id)
        trustor_project = self.get_project(
            trustor_project_name, domain_id=trustor_domain.id)

        if not roles:
            roles = default_roles

        new_trust = self.openstack_sdk.identity.create_trust(
            impersonation=impersonation,
            project_id=trustor_project.id,
            trustor_user_id=trustor_user.id,
            trustee_user_id=trustee_user.id,
            roles=roles,
            domain_id=trustee_domain.id)
        return new_trust

    def list_trusts(self):
        return [t for t in self.openstack_sdk.identity.trusts()]

    def list_projects(self, **kwargs):
        if self.identity_version > 2:
            kwargs = self._parse_domain_kwargs(kwargs, domain_override='domain')
        return self.user_manager.list_projects(**kwargs)

    def list_roles(self, **kwargs):
        """
        Keystone already accepts 'domain_name' to restrict what roles to return
        """
        return self.user_manager.keystone.roles.list(**kwargs)

    def get_role(self, role_name_or_id, **list_kwargs):
        if self.identity_version > 2:
            list_kwargs = self._parse_domain_kwargs(list_kwargs)
        role_list = self.list_roles(**list_kwargs)
        found_roles = [role for role in role_list if role.id == role_name_or_id or role.name == role_name_or_id]
        if not found_roles:
            return None
        if len(found_roles) > 1:
            raise Exception("role name/id %s matched more than one value -- Fix the code" % (role_name_or_id,))
        return found_roles[0]

    def get_user(self, user_name_or_id, **list_kwargs):
        user_list = self.list_users(**list_kwargs)
        found_users = [user for user in user_list if user.id == user_name_or_id or user.name == user_name_or_id]
        if not found_users:
            return None
        if len(found_users) > 1:
            raise Exception("User name/id %s matched more than one value -- Fix the code" % (user_name_or_id,))
        return found_users[0]

    def _parse_domain_kwargs(self, kwargs, domain_override='domain_id', default_domain='default'):
        """
        CLI's replace domain_name with the actual domain.
        We replicate that functionality to avoid operator-frustration.
        """
        domain_key = 'domain_name'
        if self.identity_version <= 2:
            return kwargs
        if domain_override in kwargs:
            if domain_key in kwargs:
                kwargs.pop(domain_key)
            return kwargs
        if domain_key not in kwargs:
            kwargs[domain_key] = default_domain # Set to default domain

        domain_name_or_id = kwargs.get(domain_key)
        domain = self.openstack_sdk.identity.find_domain(domain_name_or_id)
        if not domain:
            raise ValueError("Could not find domain %s by name or id."
                             % domain_name_or_id)
        kwargs.pop(domain_key, '')
        kwargs[domain_override] = domain.id
        return kwargs

    def list_users(self, **kwargs):
        if self.identity_version > 2:
            kwargs = self._parse_domain_kwargs(kwargs, domain_override='domain')
        return self.user_manager.keystone.users.list(**kwargs)

    def get_quota_limit(self, username, project_name):
        limits = {}
        abs_limits = self.get_absolute_limits()
        user_limits = self.get_user_limits(username, project_name)
        if abs_limits:
            limits.update(abs_limits)
        if user_limits:
            limits.update(user_limits)
        return limits

    def get_absolute_limits(self):
        limits = {}
        os_limits = self.admin_driver._connection.ex_get_limits()
        try:
            absolute_limits = os_limits['absolute']
            limits['cpu'] = absolute_limits['maxTotalCores']
            limits['floating_ips'] = absolute_limits['maxTotalFloatingIps']
            limits['instances'] = absolute_limits['maxTotalInstances']
            limits['keypairs'] = absolute_limits['maxTotalKeypairs']
            limits['ram'] = absolute_limits['maxTotalRAMSize']
        except:
            logger.exception("The method for 'reading' absolute limits has changed!")
            
        return limits

    def get_user_limits(self, username, project_name):
        limits = {}
        try:
            user_id = self.get_user(username).id
        except:
            logger.exception("Failed to find user %s" % username)
            raise ValueError ("Unknown user %s" % username)

        try:
            project_id = self.get_project(project_name).id
        except:
            logger.exception("Failed to find project %s" % project_name)
            raise ValueError ("Unknown project %s" % project_name)

        user_limits = self._ex_list_quota_for_user(user_id, project_id)

        if not user_limits:
            return limits
        try:
            user_quota = user_limits['quota_set']
            limits['cpu'] = user_quota['cores']
            limits['floating_ips'] = user_quota['floating_ips']
            limits['instances'] = user_quota['instances']
            limits['keypairs'] = user_quota['key_pairs']
            limits['ram'] = user_quota['ram']
        except:
            logger.exception("The method for 'reading' absolute limits has changed!")

        return limits

    def _ex_list_quota_for_user(self, user_id, tenant_id):
        """
        """
        server_resp = self.admin_driver._connection.connection.request('/os-quota-sets/%s?user_id=%s'
                                             % (tenant_id, user_id))
        quota_obj = server_resp.object
        return quota_obj
        



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
        # Build credentials for each manager
        all_creds = self._get_openstack_credentials(
            username, password, tenant_name)
        # Initialize managers with respective credentials
        all_clients = self.get_user_clients(all_creds)
        openstack_sdk = self.get_openstack_sdk_client(all_creds)
        neutron = self.get_neutron_client(all_creds)
        glance = self.get_glance_client(all_creds)
        all_clients.update({
            "glance": glance,
            "neutron": neutron,
            "openstack_sdk": openstack_sdk,
            "horizon": self._get_horizon_url(all_clients['keystone'].tenant_id)
        })
        return all_clients

    def get_openstack_client(self, identity, client_name):
        identity_creds = self.parse_identity(identity)
        username = identity_creds["username"]
        password = identity_creds["password"]
        project_name = identity_creds["tenant_name"]
        all_creds = self._get_openstack_credentials(
            username, password, project_name)

        if client_name == 'neutron':
            return self.get_neutron_client(all_creds)
        elif client_name == 'glance':
            return self.get_glance_client(all_creds)
        elif client_name == 'keystone':
            return self.get_user_clients(all_creds)['keystone']
        elif client_name == 'nova':
            return self.get_user_clients(all_creds)['nova']
        elif client_name == 'swift':
            return self.get_user_clients(all_creds)['swift']
        elif client_name == 'openstack':
            return self.get_openstack_sdk_client(all_creds)
        else:
            raise ValueError("Invalid client_name %s" % client_name)

    def get_glance_client(self, all_creds):
        image_creds = self._build_image_creds(all_creds)
        _, _, glance = self.image_manager._new_connection(**image_creds)
        return glance

    def get_neutron_client(self, all_creds):
        net_creds = self._build_network_creds(all_creds)
        neutron = self.network_manager.new_connection(**net_creds)
        return neutron

    def get_user_clients(self, all_creds):
        user_creds = self._build_user_creds(all_creds)
        (keystone, nova, swift) = self.user_manager.new_connection(
            **user_creds)
        return {
            "keystone": keystone,
            "nova": nova,
            "swift": swift
        }
    def get_openstack_sdk_client(self, all_creds):
        sdk_creds = self._build_sdk_creds(all_creds)
        openstack_sdk = _connect_to_openstack_sdk(**sdk_creds)
        return openstack_sdk

    def _get_openstack_credentials(self, username,
                                   password=None, tenant_name=None):
        if not tenant_name:
            tenant_name = self.get_project_name_for(username)
        if not password:
            password = self.hashpass(tenant_name)
        version = self.user_manager.keystone_version() 
        if version == 2:
            ex_version = '2.0_password'
        elif version == 3:
            ex_version = '3.x_password'

        osdk_creds = {
            "auth_url": self.user_manager.nova.client.auth_url.replace('/v3','').replace('/v2.0',''),
            "admin_url": self.user_manager.keystone._management_url.replace('/v2.0','').replace('/v3',''),
            "ex_force_auth_version": ex_version,
            "region_name": self.user_manager.nova.client.region_name,
            "username": username,
            "password": password,
            "tenant_name": tenant_name
        }
        return osdk_creds

    # Credential manipulaters
    def get_tenant_name(self, credentials):
        tenant_name = credentials.get('ex_tenant_name')
        if not tenant_name:
            tenant_name = credentials.get('tenant_name')
        if not tenant_name:
            tenant_name = credentials.get('ex_project_name')
        if not tenant_name:
            tenant_name = credentials.get('project_name')
        return tenant_name

    def _libcloud_to_openstack(self, credentials):
        credentials["username"] = credentials.pop("key")
        credentials["password"] = credentials.pop("secret")
        credentials["tenant_name"] = self.get_tenant_name(credentials)
        return credentials

    def _base_network_creds(self):
        """
        These credentials should be used when another user/pass/tenant
        combination will be used
        NOTE: JETSTREAM auth_url to be '/v3'
        """
        net_args = self.provider_creds.copy()
        # NOTE: The neutron 'auth_url' is the ADMIN_URL
        net_args['tenant_name'] = self.get_tenant_name(self.credentials)
        net_args["auth_url"] = net_args.pop("admin_url")\
            .replace("/tokens", "").replace('/v2.0', '').replace('/v3', '')
        if self.identity_version == 3:
            auth_prefix = '/v3'
        elif self.identity_version == 2:
            auth_prefix = '/v2.0'

        if auth_prefix not in net_args['auth_url']:
            net_args['auth_url'] += auth_prefix
        return net_args

    def _build_network_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "NetworkManager" object
        NOTE: JETSTREAM auth_url to be '/v3'
        """
        net_args = credentials.copy()
        # Required:
        net_args.get("username")
        net_args.get("password")
        net_args.get("tenant_name")

        net_args.get("router_name")
        net_args.get("region_name")
        # NOTE: The neutron 'auth_url' is the ADMIN_URL
        net_args["auth_url"] = net_args.pop("admin_url").replace("/tokens", "")
        # Ignored:
        net_args.pop("location", None)
        net_args.pop("ex_project_name", None)
        net_args.pop("ex_force_auth_version", None)
        auth_url = net_args.get('auth_url')
        if self.identity_version == 3:
            auth_prefix = '/v3'
        elif self.identity_version == 2:
            auth_prefix = '/v2.0'

        net_args["auth_url"] = auth_url.replace("/v2.0", "").replace('/v3', '').replace("/tokens", "")
        if auth_prefix not in net_args['auth_url']:
            net_args["auth_url"] += auth_prefix
        return net_args

    def _build_image_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "UserManager" object
        NOTE: Expects auth_url to be '/v2.0/tokens'
        NOTE: JETSTREAM auth_url to be '/v3'
        """
        img_args = credentials.copy()
        img_args['tenant_name'] = self.get_tenant_name(credentials)
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
        ex_auth_version = img_args.get("ex_force_auth_version", '2.0_password')
        # Supports v2.0 or v3 Identity
        if ex_auth_version.startswith('2'):
            auth_url_prefix = "/v2.0/tokens"
            auth_version = 'v2.0'
        elif ex_auth_version.startswith('3'):
            auth_url_prefix = "/v3/tokens"
            auth_version = 'v3'
        img_args['version'] = auth_version

        img_args["auth_url"] = img_args.get('auth_url','').replace("/v2.0","").replace("/tokens", "").replace('/v3','')
        if auth_url_prefix not in img_args['auth_url']:
            img_args["auth_url"] += auth_url_prefix
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
        user_args["tenant_name"] = self.get_tenant_name(credentials)
        ex_auth_version = user_args.pop("ex_force_auth_version", '2.0_password')
        # Supports v2.0 or v3 Identity
        if ex_auth_version.startswith('2'):
            auth_url_prefix = "/v2.0/"
            auth_version = 'v2.0'
        elif ex_auth_version.startswith('3'):
            auth_url_prefix = "/v3/"
            auth_version = 'v3'

        auth_url = user_args.get('auth_url')
        user_args["auth_url"] = auth_url.replace("/v2.0", "").replace("/tokens", "")
        if auth_url_prefix not in user_args['auth_url']:
            user_args["auth_url"] += auth_url_prefix
        user_args.get("region_name")
        user_args['version'] = user_args.get("version", auth_version)
        # Removable args:
        user_args.pop("admin_url", None)
        user_args.pop("location", None)
        user_args.pop("router_name", None)
        user_args.pop("ex_project_name", None)

        return user_args

    def _build_sdk_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build an "Openstack SDK" connection
        NOTE: Expects auth_url to be ADMIN aand be '/v3'
        """
        os_args = credentials.copy()
        # Required args:
        os_args.get("username")
        os_args.get("password")
        os_args['project_name'] = self.get_tenant_name(os_args)
        os_args.get("region_name")

        ex_auth_version = os_args.pop("ex_force_auth_version", '2.0_password')
        # Supports v2.0 or v3 Identity
        if ex_auth_version.startswith('2'):
            auth_url_prefix = "/v2.0/"
            auth_version = 'v2.0'
        elif ex_auth_version.startswith('3'):
            auth_url_prefix = "/v3/"
            auth_version = 'v3'
        os_args["auth_url"] = os_args.get("auth_url")\
            .replace("/tokens", "").replace('/v2.0', '').replace('/v3', '')

        # NOTE: Openstack 'auth_url' is ACTUALLY the admin url.
        if auth_url_prefix not in os_args['admin_url']:
            os_args["auth_url"] = os_args['admin_url'] + auth_url_prefix

        if 'project_domain_name' not in os_args:
            os_args['project_domain_name'] = 'default'
        if 'user_domain_name' not in os_args:
            os_args['user_domain_name'] = 'default'
        if 'identity_api_version' not in os_args:
            os_args['identity_api_version'] = 3 #NOTE: this is what we use to determine whether or not to make openstack_sdk
        # Removable args:
        os_args.pop("ex_force_auth_version", None)
        os_args.pop("admin_url", None)
        os_args.pop("location", None)
        os_args.pop("router_name", None)
        os_args.pop("ex_project_name", None)
        os_args.pop("ex_tenant_name", None)
        os_args.pop("tenant_name", None)
        return os_args
