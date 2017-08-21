"""
Driver factory (non-standard mock but useful for testing)
"""
import collections
import copy
import uuid

from threepio import logger

from rtwo.models.instance import Instance
from rtwo.models.size import MockSize
from rtwo.driver import MockDriver
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.common import _connect_to_keystone_v3, _token_to_keystone_scoped_project

# Globals..
ALL_VOLUMES = []
ALL_INSTANCES = []
ALL_MACHINES = []
ALL_SIZES = []
ALL_NETWORKS = []
ALL_SUBNETS = []
ALL_ROUTERS = []
ALL_PORTS = []
ALL_IPS = []


class AtmosphereMockNetworkManager(NetworkManager):
    """
    NOTE: Mock manager is likely more-than-feature-complete
    Once we are sure that no other overrides are necessary, we can cull the extra methods.
    """

    def __init__(self, *args, **kwargs):
        self.neutron = None
        self.default_router = None
        self.all_networks = ALL_NETWORKS
        self.all_subnets = ALL_SUBNETS
        self.all_routers = ALL_ROUTERS
        self.all_ports = ALL_PORTS

    @staticmethod
    def create_manager(core_identity):
        return AtmosphereMockNetworkManager(
            core_identity)

    def tenant_networks(self, tenant_id=None):
        return []

    def get_tenant_id(self):
        return 1

    def get_credentials(self):
        """
        Return the user_id and tenant_id of the network manager
        """
        return {
                'user_id':1,
                'tenant_id':1
            }

    def disassociate_floating_ip(self, server_id):
        return '0.0.0.0'

    def associate_floating_ip(self, server_id):
        return '0.0.0.0'

    def create_port(self, server_id, network_id, **kwargs):
        port = kwargs
        self.all_ports.append(port)
        return port

    def find_server_ports(self, server_id):
        return self.all_ports

    def list_floating_ips(self):
        return ['0.0.0.0']

    def rename_security_group(self, project, security_group_name=None):
        return True

    def lc_list_networks(self, *args, **kwargs):
        """
        Call neutron list networks and convert to libcloud objects
        """
        return []

    def get_network(self, network_id):
        for net in self.all_networks:
            if network_id == net['id']:
                return net
        return None

    def get_subnet(self, subnet_id):
        for subnet in self.all_subnets:
            if subnet_id == subnet['id']:
                return subnet
        return None

    def get_port(self, port_id):
        ports = self.all_ports
        if not ports:
            return []
        for port in ports:
            if port['id'] == port_id:
                return port
        return None

    def list_networks(self, *args, **kwargs):
        """
        NOTE: kwargs can be: tenant_id=, or any other attr listed in the
        details of a network.
        """
        return self.all_networks

    def list_subnets(self):
        return self.all_subnets

    def list_routers(self):
        return self.all_routers

    def list_ports(self, **kwargs):
        """
        Options:
        subnet_id=subnet.id
        device_id=device.id
        ip_address=111.222.333.444
        """
        return self.all_ports

    def create_network(self, neutron, network_name):
        network = {'name': network_name, 'admin_state_up': True}
        self.all_networks.append(network)
        return network

    def validate_cidr(self, cidr):
        return True

    def create_subnet(self, neutron, subnet_name,
                      network_id, ip_version=4, cidr=None,
                      dns_nameservers=[], subnet_pool_id=None):
        subnet = {
            'name': subnet_name,
            'network_id': network_id,
            'ip_version': ip_version,
        }
        if subnet_pool_id:
            subnet['subnetpool_id'] = subnet_pool_id
        else:
            if not dns_nameservers:
                dns_nameservers = ['8.8.8.8', '8.8.4.4']
            subnet['dns_nameservers'] = dns_nameservers
            subnet['cidr'] = cidr
        logger.debug("Creating subnet - %s" % subnet)
        self.all_subnets.append(subnet)
        return subnet

    def create_router(self, neutron, router_name):
        existing_routers = self.find_router(router_name)
        if existing_routers:
            logger.info('Router %s already exists' % router_name)
            return existing_routers[0]
        router = {'name': router_name, 'admin_state_up': True}
        self.all_routers.append(router)
        return router

    def add_router_interface(self, router, subnet, interface_name=None):
        interface_obj = {"name":interface_name}
        return interface_obj

    def set_router_gateway(self, neutron, router_name,
                           external_network_name='ext_net'):
        """
        Must be run as admin
        """
        body = {'router_id': router_name, 'network_id': external_network_name}
        return body

    def remove_router_gateway(self, router_name):
        return

    def remove_router_interface(self, neutron, router_name, subnet_name):
        return

    def delete_router(self, neutron, router_name):
        return

    def delete_subnet(self, neutron, subnet_name):
        return

    def delete_network(self, neutron, network_name):
        return

    def delete_port(self, port):
        return


class MockInstance(Instance):
    def __init__(self, id=None, provider=None, source=None, ip=None, size=None, extra={}, *args, **kwargs):
        identifier = id
        if not identifier:
            identifier = kwargs.get('uuid', uuid.uuid4())
        if not size:
            size = MockSize("Unknown", provider)
        if not ip:
            ip = '0.0.0.0'
        self.id = identifier
        self.alias = identifier
        self.provider = provider
        self.size = size
        self.name = kwargs.get('name', "Mock instance %s" % identifier)
        self.source = source
        self.ip = ip
        self._node = None
        self.extra = extra

    def json(self):
        return self.__dict__




class AtmosphereMockDriver(MockDriver):

    all_volumes = ALL_VOLUMES
    all_instances = ALL_INSTANCES
    all_machines = ALL_MACHINES
    all_sizes = ALL_SIZES

    def is_valid(self):
        """
        Performs validation on the driver -- for most drivers, this will mean you actually have to _call something_ on the API. if it succeeds, the driver is valid.
        """
        return True

    def _get_size(self, alias):
        size = MockSize("Unknown", self.providerCls() )
        return size


    def list_all_volumes(self, *args, **kwargs):
        """
        Return the InstanceClass representation of a libcloud node
        """
        return self.all_volumes

    def list_all_instances(self, **kwargs):
        """
        Return the InstanceClass representation of a libcloud node
        """
        return self.all_instances

    def get_instance(self, instance_id, *args, **kwargs):
        """
        Return the InstanceClass representation of a libcloud node
        """
        instances = self.list_all_instances()
        instance = [inst for inst in instances if inst.id == instance_id]
        if not instance:
            return None
        return instance[0]

    def add_core_instance(self, core_instance):
        extra = {}
        extra['metadata'] = {'iplant_suspend_fix': False, 'tmp_status': ''}
        extra['status'] = core_instance.get_last_history().status.name
        esh_instance = self.create_instance(
            id=str(core_instance.provider_alias),
            ip=core_instance.ip_address,
            name=core_instance.name,
            extra=extra)
        return esh_instance

    def list_instances(self, **kwargs):
        """
        Return the InstanceClass representation of a libcloud node
        """
        return self.all_instances

    def list_machines(self, *args, **kwargs):
        """
        Return the MachineClass representation of a libcloud NodeImage
        """
        return self.all_machines

    def list_sizes(self, *args, **kwargs):
        """
        Return the SizeClass representation of a libcloud NodeSize
        """
        return self.all_sizes

    def list_locations(self, *args, **kwargs):
        return []

    def create_instance(self, *args, **kwargs):
        """
        Return the InstanceClass representation of a libcloud node
        """
        new_instance = MockInstance(*args, **kwargs)
        self.all_instances.append(new_instance)
        return new_instance

    def deploy_instance(self, *args, **kwargs):
        return True

    def reset_network(self, *args, **kwargs):
        return True

    def reboot_instance(self, *args, **kwargs):
        return True

    def start_instance(self, *args, **kwargs):
        return True

    def stop_instance(self, *args, **kwargs):
        return True

    def resume_instance(self, *args, **kwargs):
        return True

    def confirm_resize(self, *args, **kwargs):
        return True

    def resize_instance(self, *args, **kwargs):
        return True

    def suspend_instance(self, *args, **kwargs):
        return True

    def destroy_instance(self, new_instance, *args, **kwargs):
        index = self.all_instances.index(new_instance)
        return self.all_instances.pop(index)

    def boot_volume(self, *args, **kwargs):
        raise NotImplementedError()

    def list_volumes(self, *args, **kwargs):
        return self.all_volumes

    def create_volume(self, *args, **kwargs):
        volume_args = copy.copy(kwargs)
        volume_args.pop('max_attempts', None)
        volume_args['id'] = volume_args.get('id', str(uuid.uuid4()))
        volume_args['extra'] = volume_args.get('extra', {})
        MockESHVolume = collections.namedtuple('MockESHVolume',
                                               ['id', 'name', 'image', 'snapshot', 'metadata', 'size', 'extra'])
        mock_volume = MockESHVolume(**volume_args)
        self.all_volumes.append(mock_volume)
        return True, mock_volume

    def destroy_volume(self, *args, **kwargs):
        raise NotImplementedError()

    def attach_volume(self, *args, **kwargs):
        raise NotImplementedError()

    def detach_volume(self, *args, **kwargs):
        raise NotImplementedError()
