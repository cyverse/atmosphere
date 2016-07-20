"""
Atmosphere network

This file will help a driver infer the strategy to use when creating or destroying a "project network".

For more information, see docs/NETWORKING.md
"""
import random

from rtwo.exceptions import NeutronClientException, NeutronNotFound

from atmosphere import settings
from threepio import logger


def topology_list():
    return [
        #GenericNetworkTopology,
        ExternalNetwork,
        ExternalRouter,
    ]


def _generate_ssh_kwargs(timeout=120):
    kwargs = {}
    kwargs.update({'ssh_key': settings.ATMOSPHERE_PRIVATE_KEYFILE})
    kwargs.update({'timeout': timeout})
    return kwargs

def _get_unique_id(userid):
    if 'iplantauth.authBackends.LDAPLoginBackend' in settings.AUTHENTICATION_BACKENDS:
        from iplantauth.protocol.ldap import _get_uid_number
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

    #16-31
    block1 = (n + inc) % 16 + 16

    #1-254
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
    This network topology describes how networks should be created per openstack project.
    """
    name = None
    user_network_required = False
    user_router_required = False
    options = {}

    # Standard implementation for Network Topology
    def __init__(self, identity):
        pass

    def configure(self, **options):
        self.options.update(options)

    def validate(self, core_identity):
        """
        Basic assertions, like 'username', 'project_name', 'password' could be added here...
        """
        return True

    def get_or_create_network(self, network_driver, user_neutron, network_name):
        network = network_driver.create_network(user_neutron, network_name)
        return network

    def get_or_create_user_subnet(
            self, network_driver, neutron,
            network_id, username, subnet_name,
            ip_version=4, dns_nameservers=[],
            get_unique_number=_get_unique_id,
            get_cidr=get_default_subnet):
        """
        Create a subnet for the user using the get_cidr function to get
        a private subnet range.
        """
        success = False
        inc = 0
        MAX_SUBNET = 4064
        cidr = None
        while not success and inc < MAX_SUBNET:
            try:
                cidr = get_cidr(username, inc, get_unique_number)
                if cidr:
                    return network_driver.create_subnet(neutron, subnet_name,
                                              network_id, ip_version,
                                              cidr, dns_nameservers)
                else:
                    logger.warn("Unable to create cidr for subnet "
                                "for user: %s" % username)
                    inc += 1
            except NeutronClientException as nce:
                if "overlap" in nce.message:
                    # expected output. hash already use, add one and try another subnet.
                    inc += 1
                else:
                    logger.exception("Unable to create subnet for user: %s" % username)
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
        if not success or not cidr:
            raise Exception("Unable to create subnet for user: %s" % username)

    def get_or_create_router(self, network_driver, user_neutron, router_name, subnet):
        router = network_driver.create_router(
            user_neutron, router_name)
        return router

    def get_or_create_router_gateway(self, network_driver, user_neutron, router, network):
        gateway = network_driver.set_router_gateway(
            user_neutron, router.name, network.name)
        return gateway

    def get_or_create_router_interface(self, network_driver, user_neutron, router, subnet, interface_name):
        interface = network_driver.add_router_interface(
            router, subnet, interface_name)
        return interface

    #NOTE: Reversed order for deletes.
    def delete_router_interface(self, network_driver, user_neutron,
                                router_name, subnet_name):
        try:
            interface = network_driver.remove_router_interface(
                network_driver.neutron, router_name, subnet_name)
        except NeutronNotFound:
            #This is OKAY!
            return None
        except:
            raise
        return interface

    def delete_router_gateway(self, network_driver, user_neutron, router_name):
        return network_driver.remove_router_gateway(router_name)

    def delete_router(self, network_driver, user_neutron, router_name):
        return network_driver.delete_router(user_neutron, router_name)

    def delete_network(self, network_driver, user_neutron, network_name):
        return network_driver.delete_network(user_neutron, network_name)

    def delete_subnet(self, network_driver, user_neutron, subnet_name):
        """
        NOTE: If you see errors like the one below when you attempt to delete
        the users network, and no instances remain, you are likely
        not removing the router interface.
        ```
            Conflict: Unable to complete operation on subnet 1-2-3-4.
                      One or more ports have an IP allocation from this subnet.
        ```
        """
        return network_driver.delete_subnet(user_neutron, subnet_name)


class ExternalNetwork(GenericNetworkTopology):
    """
    This topology assumes:
    user_subnet --> user_router --> interface --> external_network
    """
    name = "External Network Topology"
    external_network_name = None
    user_subnet_required = True
    user_network_required = False
    user_router_required = True

    def __init__(self, identity):
        network_name = identity.get_credential('network_name')
        if not network_name:
            network_name = identity.provider.get_credential('network_name')
        if not network_name:
            raise Exception("Unknown Network - Identity %s is missing 'network_name' " % identity)
        self.external_network_name = network_name

    def validate(self, core_identity):
        identity_creds = core_identity.get_all_credentials()
        if 'network_name' not in identity_creds.keys():
            logger.warn("Credential 'network_name' missing:"
                        "cannot create user network")
            raise Exception("Identity %s has not been assigned a 'network_name'" % core_identity)
        return True

    def delete_network(self, network_driver, user_neutron, network_name):
        return None

    def get_or_create_network(self, network_driver, user_neutron, network_name):
        # Step 1. Does public network exist?
        public_network = network_driver.find_network(
            self.external_network_name)
        if type(public_network) == list:
            public_network = public_network[0]
        elif not public_network:
            raise Exception(
                "Default external network %s was not found -- "
                "Required when using ExternalNetwork."
                % self.external_network_name)
        return public_network


    def get_or_create_router_interface(self, network_driver, user_neutron, router, subnet, interface_name):
        #TODO: Determine if this is required in this Topology or not.
        # interface = network_driver.add_router_interface(
        #     router, subnet, interface_name)
        # return interface
        return None

class ExternalRouter(GenericNetworkTopology):
    """
    This topology assumes:
    user_network --> user_subnet --> interface --> external_router
    """
    name = "External Router Topology"
    external_network_name = None
    user_subnet_required = True
    user_network_required = True
    user_router_required = False

    def __init__(self, identity):
        router_name = identity.get_credential('router_name')
        if not router_name:
            router_name = identity.provider.get_credential('router_name')
        if not router_name:
            raise Exception("Unknown Router - Identity %s is missing 'router_name' " % identity)
        self.external_router_name = router_name

    def validate(self, core_identity):
        identity_creds = core_identity.get_all_credentials()
        if 'router_name' not in identity_creds.keys():
            logger.warn("Credential 'router_name' missing:"
                        "cannot create user network")
            raise Exception("Identity %s has not been assigned a 'router_name'" % core_identity)
        return True

    def delete_router(self, network_driver, user_neutron, router_name):
        return None

    def delete_router_gateway(self, network_driver, user_neutron, router_name):
        return None

    def delete_router_interface(self, network_driver, user_neutron,
                                router_name, subnet_name):
        return super(ExternalRouter, self).delete_router_interface(
            network_driver, user_neutron,
            self.external_router_name,  # strategy choice
            subnet_name)

    def get_or_create_router_gateway(self, network_driver, user_neutron, router, network):
        return None

    def get_or_create_router(self, network_driver, user_neutron, router_name):
        router_name = self.external_router_name  # strategy choice
        public_router = network_driver.find_router(router_name)
        if not public_router:
            raise Exception("Default public router %s was not found." % self.external_router_name)
        return public_router[0]

