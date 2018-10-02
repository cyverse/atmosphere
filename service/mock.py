"""
Driver factory (non-standard mock but useful for testing)
"""
import collections
import copy
import uuid
import random
import warlock

from threepio import logger

from rtwo.models.instance import Instance
from rtwo.models.size import MockSize
from rtwo.driver import MockDriver
from rtwo.drivers.openstack_network import NetworkManager
from service.accounts.base import BaseAccountDriver

from glanceclient.v2.image_schema import _BASE_SCHEMA as GLANCE_IMAGE_SCHEMA
# Globals..
ALL_GLANCE_IMAGES = []
ALL_VOLUMES = []
ALL_INSTANCES = []
ALL_MACHINES = []
ALL_SIZES = []
ALL_NETWORKS = []
ALL_SUBNETS = []
ALL_ROUTERS = []
ALL_PORTS = []


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
        return AtmosphereMockNetworkManager(core_identity)

    def tenant_networks(self, tenant_id=None):
        return []

    def get_tenant_id(self):
        return 1

    def get_credentials(self):
        """
        Return the user_id and tenant_id of the network manager
        """
        return {'user_id': 1, 'tenant_id': 1}

    def disassociate_floating_ip(self, server_id):
        return '0.0.0.0'

    def associate_floating_ip(self, server_id):
        return '0.0.0.0'

    def list_floating_ips(self):
        return ['0.0.0.0']

    def rename_security_group(self, project, security_group_name=None):
        return True

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

    def create_subnet(
        self,
        neutron,
        subnet_name,
        network_id,
        ip_version=4,
        cidr=None,
        dns_nameservers=[],
        subnet_pool_id=None
    ):
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
        interface_obj = {"name": interface_name}
        return interface_obj

    def set_router_gateway(
        self, neutron, router_name, external_network_name='ext_net'
    ):
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
    def __init__(
        self,
        id=None,
        provider=None,
        source=None,
        ip=None,
        size=None,
        extra={},
        *args,
        **kwargs
    ):
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
        Performs validation on the driver -- for most drivers,
        this will mean you actually have to _call something_ on the API.
        if it succeeds, the driver is valid.
        """
        return True

    def _get_size(self, alias):
        size = MockSize("Unknown", self.providerCls())
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
            extra=extra
        )
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
        MockESHVolume = collections.namedtuple(
            'MockESHVolume',
            ['id', 'name', 'image', 'snapshot', 'metadata', 'size', 'extra']
        )
        mock_volume = MockESHVolume(**volume_args)
        self.all_volumes.append(mock_volume)
        return True, mock_volume

    def destroy_volume(self, *args, **kwargs):
        raise NotImplementedError()

    def attach_volume(self, *args, **kwargs):
        raise NotImplementedError()

    def detach_volume(self, *args, **kwargs):
        raise NotImplementedError()


class MockAccountDriver(BaseAccountDriver):
    def __init__(self):
        self.glance_images = ALL_GLANCE_IMAGES
        self.project_name = "admin"
        self.GlanceImage = warlock.model_factory(GLANCE_IMAGE_SCHEMA)
        return

    def get_project_by_id(self, project_id):
        PROJECT_SCHEMA = {
            'name':
                {
                    'type': ['null', 'string'],
                    'description': 'name of the project/tenant',
                    'maxLength': 255
                }
        }
        MockProject = warlock.model_factory(PROJECT_SCHEMA)
        if not project_id:
            return None
        elif 'admin' in project_id.lower():
            return MockProject(name='admin')
        else:
            return MockProject(name='UnknownUser')

    def _generate_glance_image(self, **kwargs):
        identifier = kwargs.pop('id', uuid.uuid4())
        defaults = {
            'checksum': 'fakefake0notrealnotreal0fakefake',
            'container_format': 'bare',
            'created_at': '2017-10-19T08:00:00Z',
            'updated_at': '2017-10-19T08:00:00Z',
            'owner': 'fakeADMINfake1234fakse1234fake00',
            'id': identifier,
            'size': int(random.uniform(10, 20)) * 1024**3,
            'container_format': 'bare',
            'disk_format': 'qcow2',
            'file': "/v2/images/%s/file" % identifier,
            'schema': '/v2/schemas/image',
            'status': 'active',
            'visibility': 'public',
            'min_disk': 0,
            'min_ram': 0,
            'name': "Mock glance image",
            'protected': False,
            'tags': [],
        # Extra properties
            'application_description': u'New application description',
            'application_name': u'Test Application',
            'application_owner': u'admin',
            'application_tags': u'["test", "test2"]',
            'application_uuid': u'2703ef14-c346-57bd-805a-9bbfae4ad54e',
            'version_changelog': u'Test Version',
            'version_name': u'1.0-test',
        }
        defaults.update(kwargs)
        return self.GlanceImage(**defaults)

    def generate_images(self, count=10, **generate_with_kwargs):
        for x in xrange(1, count + 1):
            overrides = {
                "id": "deadbeef-dead-dead-beef-deadbeef%04d" % x,
                "name": "Test glance image %04d" % x,
                "application_name": "Test Application %04d" % x,
                "version_name": "v%d.0-test" % x
            }
            glance_image = self._generate_glance_image(**overrides)
            self.glance_images.append(glance_image)

    def clear_images(self):
        global ALL_GLANCE_IMAGES
        ALL_GLANCE_IMAGES = []
        self.glance_images = ALL_GLANCE_IMAGES
        return True

    def _list_all_images(self, *args, **kwargs):
        return self.glance_images

    def _get_image(self, identifier, *args, **kwargs):
        for image in self.glance_images:
            if image.get('id') == identifier:
                return image
        return None
