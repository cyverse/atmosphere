"""
Atmosphere network

This file will help a driver infer the strategy to use when creating or
destroying a "project network".

For more information, see docs/NETWORKING.md
"""
import random

from rtwo.exceptions import NeutronClientException, NeutronNotFound

from atmosphere import settings
from threepio import logger


def topology_list():
    return [
        ExternalNetwork,
        ExternalRouter,
    ]


def _generate_ssh_kwargs(timeout=120):
    kwargs = {}
    kwargs.update({'ssh_key': settings.ATMOSPHERE_PRIVATE_KEYFILE})
    kwargs.update({'timeout': timeout})
    return kwargs

def _get_unique_id(userid):
    if 'django_cyverse_auth.authBackends.LDAPLoginBackend' in \
            settings.AUTHENTICATION_BACKENDS:
        from django_cyverse_auth.protocol.ldap import _get_uid_number
        return _get_uid_number(userid)
    else:
        return _get_random_uid(userid)


def _get_random_uid(userid):
    """
    Given a string (Username) return a value < MAX_SUBNET
    """
    MAX_SUBNET = 4064
    return int(random.uniform(1, MAX_SUBNET))


def get_topology_cls(topology_name):
    if topology_name == ExternalNetwork.name:
        return ExternalNetwork
    elif topology_name == ExternalRouter.name:
        return ExternalRouter
    else:
        raise Exception("Unknown topology name %s" % topology_name)


def get_ranges(uid_number, inc=0):
    """
    Return two block ranges to be used to create subnets for
    Atmosphere users.

    NOTE: If you change MAX_SUBNET then you should likely change
    the related math.
    """
    MAX_SUBNET = 4064  # Note 16 * 256
    n = uid_number % MAX_SUBNET

    # 16-31
    block1 = (n + inc) % 16 + 16

    # 1-254
    block2 = ((n + inc) / 16) % 254 + 1

    return (block1, block2)


def get_default_subnet(username, inc=0, get_uid_number=None):
    """
    Return the default subnet for the username and provider.

    Add and mod by inc to allow for collitions.
    """
    if get_uid_number:
        uid_number = get_uid_number(username)
    else:
        uid_number = 0

    if uid_number:
        (block1, block2) = get_ranges(uid_number, inc)
    else:
        (block1, block2) = get_ranges(0, inc)

    return "172.%s.%s.0/24" % (block1, block2)


class GenericNetworkTopology(object):
    """
    This network topology describes how networks should be created per
    openstack project.
    """
    name = None

    # Standard implementation for Network Topology
    def __init__(self, identity, network_driver, neutron):
        self.network_driver = network_driver
        self.user_neutron = neutron
        self.identity = identity
        # Note:
        # it is necessary that the identity doesn't change after this object's
        # creation, or this prefix will be old
        self.prefix = identity.get_credential('ex_project_name')

    def delete(self, skip_network=False):
        """
        Delegates deletion behavior to child classes
        """
        raise NotImplementedError

    def create(self, username=None, dns_nameservers=None):
        """
        Delegates creation behavior to child classes
        """
        raise NotImplementedError

    def validate(self, core_identity):
        """
        Basic assertions, like 'username', 'project_name', 'password' could be
        added here...
        """
        return True

    def post_create_hook(self, network_resources_dict):
        """
        Given the options in your strategy and your newly created resources,
        use this space to "make the connections"
        """
        pass

    def get_or_create_network(self):
        network_name = "%s-net" % self.prefix
        if self.network_driver:
            return self.network_driver.create_network(
                    self.user_neutron, network_name)
        else:
            return self.user_neutron.create_network(
                {'network': {'name': network_name}})

    def get_or_create_user_subnet(
            self, network_id, username,
            ip_version=4,
            dns_nameservers=[],
            get_unique_number=_get_unique_id,
            get_cidr=get_default_subnet):
        """
        Create a subnet for the user using the get_cidr function to get
        a private subnet range.
        """
        # FIXME: Remove the username dependency -- if its just a seed value?
        # FIXME: Look into get_cidr and get_unique_number -- is there a better
        # way?
        subnet_name = "%s-subnet" % self.prefix
        success = False
        inc = 0
        MAX_SUBNET = 4064
        new_cidr = None
        while not success and inc < MAX_SUBNET:
            try:
                new_cidr = get_cidr(username, inc, get_unique_number)
                cidr_match = any(sn for sn in self.network_driver.list_subnets() if sn['cidr'] == new_cidr)
                if new_cidr and not cidr_match:
                    return self.network_driver.create_subnet(
                            self.user_neutron, subnet_name,
                            network_id, ip_version,
                            new_cidr, dns_nameservers)
                elif cidr_match:
                    logger.warn("Unable to create new_cidr for subnet "
                                "for user: %s (CIDR already used)" % username)
                    inc += 1
                else:
                    logger.warn("Unable to create new_cidr for subnet "
                                "for user: %s (create_subnet failed)" % username)
                    inc += 1
            except NeutronClientException as nce:
                if "overlap" in nce.message:
                    # Expected output. Hash is already used, add one and try
                    # another subnet.
                    inc += 1
                else:
                    logger.exception(
                            "Unable to create subnet for user: %s" % username)
                    inc += 1
                if not get_unique_number:
                    logger.warn("No get_unique_number method "
                                "provided for user: %s" % username)
            except Exception as e:
                logger.exception("Unable to create subnet for user: %s" % username)
                if not get_unique_number:
                    logger.warn("No get_unique_number method "
                                "provided for user: %s" % username)
                inc += 1
        if not success or not new_cidr:
            raise Exception("Unable to create subnet for user: %s" % username)

    def get_or_create_router(self):
        router_name = "%s-router" % self.prefix
        router = self.network_driver.create_router(
            self.user_neutron, router_name)
        return router

    def get_or_create_router_interface(self, router, subnet):
        interface_name = '%s-router-intf' % self.prefix
        interface = self.network_driver.add_router_interface(
            router, subnet, interface_name)
        return interface

    # NOTE: Reversed order for deletes.
    def delete_router_interface(self, router_name="", subnet_name=""):
        router_name = router_name or "%s-router" % self.prefix
        subnet_name = subnet_name or "%s-subnet" % self.prefix
        try:
            interface = self.network_driver.remove_router_interface(
                self.network_driver.neutron, router_name, subnet_name)
        except NeutronNotFound:
            #This is OKAY!
            return None
        except:
            raise
        return interface

    def delete_subnet(self):
        """
        NOTE: If you see errors like the one below when you attempt to delete
        the users network, and no instances remain, you are likely
        not removing the router interface.
        ```
            Conflict: Unable to complete operation on subnet 1-2-3-4.
                      One or more ports have an IP allocation from this subnet.
        ```
        """
        subnet_name = "%s-subnet" % self.prefix
        return self.network_driver.delete_subnet(self.user_neutron, subnet_name)


class ExternalNetwork(GenericNetworkTopology):
    """
    This topology assumes:
    user_network --> user_subnet --> user_router --> interface --> external_network
    """
    name = "External Network Topology"
    external_network_name = None

    def __init__(self, identity, network_driver, neutron):
        network_name = identity.get_credential('network_name')
        if not network_name:
            network_name = identity.provider.get_credential('network_name')
        if not network_name:
            raise Exception("Unknown Network - Identity %s is missing 'network_name' " % identity)
        self.external_network_name = network_name
        return super(ExternalNetwork, self).__init__(identity, network_driver, neutron)

    def get_public_network(self):
        """
        This method is special to ExternalNetwork
        """
        public_network = self.network_driver.find_network(
            self.external_network_name)
        if type(public_network) == list:
            public_network = public_network[0]
        elif not public_network:
            raise Exception(
                "Default external network %s was not found -- "
                "Required when using ExternalNetwork."
                % self.external_network_name)
        return public_network

    def validate(self, core_identity):
        identity_creds = core_identity.get_all_credentials()
        if 'network_name' not in identity_creds.keys():
            logger.warn("Credential 'network_name' missing:"
                        "cannot create user network")
            raise Exception("Identity %s has not been assigned a 'network_name'" % core_identity)
        return True

    def delete(self, skip_network=False):
        self.delete_router_interface()
        self.delete_router()
        self.delete_subnet()

    def create(self, username=None, dns_nameservers=None):
        network = self.get_or_create_network()  #NOTE: This also might be wrong.
        subnet = self.get_or_create_user_subnet(
            network['id'], username,
            dns_nameservers=dns_nameservers)
        router = self.get_or_create_router()
        gateway = self.get_or_create_router_gateway(router, network)
        interface = self.get_or_create_router_interface(
            router, subnet)
        network_resources = {
            'network': network,
            'gateway': gateway,
            'subnet': subnet,
            'router': router,
            'interface': interface,
        }
        return network_resources

    def delete_router(self):
        router_name = "%s-router" % self.prefix
        self.network_driver.delete_router(
            self.user_neutron,
            router_name)

    def get_or_create_router_gateway(self, router, network):
        public_network = self.get_public_network()
        gateway = self.network_driver.set_router_gateway(
            self.user_neutron, router['name'], public_network['name'])
        return gateway


class ExternalRouter(GenericNetworkTopology):
    """
    This topology assumes:
    user_network --> user_subnet --> interface --> external_router
    """
    name = "External Router Topology"

    def __init__(self, identity, network_driver, neutron):
        router_name = identity.get_credential('router_name')
        if not router_name:
            router_name = identity.provider.get_credential('router_name')
        if not router_name:
            raise Exception("Unknown Router - Identity %s is missing 'router_name' " % identity)
        self.external_router_name = router_name
        return super(ExternalRouter, self).__init__(identity, network_driver, neutron)

    def validate(self, core_identity):
        identity_creds = core_identity.get_all_credentials()
        if 'router_name' not in identity_creds.keys():
            logger.warn("Credential 'router_name' missing:"
                        "cannot create user network")
            raise Exception("Identity %s has not been assigned a 'router_name'" % core_identity)
        return True

    def create(self, username=None, dns_nameservers=None):
        network = self.get_or_create_network()
        subnet = self.get_or_create_user_subnet(
            network['id'], username,
            dns_nameservers=dns_nameservers)
        router = self.get_or_create_router()
        gateway = self.get_or_create_router_gateway(router, network)
        interface = self.get_or_create_router_interface(router, subnet)
        network_resources = {
            'network': network,
            'gateway': gateway,
            'subnet': subnet,
            'router': router,
            'interface': interface,
        }
        return network_resources

    def delete(self, skip_network=False):
        self.delete_router_interface()
        self.delete_subnet()
        if not skip_network:
            self.delete_network()

    def delete_network(self):
        network_name = "%s-net" % self.prefix
        self.network_driver.delete_network(
            self.user_neutron,
            network_name)

    def delete_router_interface(self):
        return super(ExternalRouter, self).delete_router_interface(
            router_name=self.external_router_name)  # strategy choice

    def get_or_create_router(self):
        router_name = self.external_router_name  # strategy choice
        public_router = self.network_driver.find_router(router_name)
        if not public_router:
            raise Exception("Default public router %s was not found." % self.external_router_name)
        return public_router[0]


    def get_or_create_router_gateway(self, router, network):
        return None
