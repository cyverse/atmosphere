"""
Driver factory (non-standard mock but useful for testing)
"""
import collections
import copy
import uuid
import random
import warlock
import mock

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
ALL_IPS = []


class AtmosphereMockNetworkManager(NetworkManager):
    """
    NOTE: Mock manager is likely more-than-feature-complete
    Once we are sure that no other overrides are necessary, we can cull the extra methods.
    """

    def __init__(self, core_identity):
        self.core_identity = core_identity
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

    def get_tenant_id(self):
        return self.core_identity.get_credential('ex_tenant_name')

    def get_credentials(self):
        """
        Return the user_id and tenant_id of the network manager
        """
        return {
                'user_id': 1,
                'tenant_id': 1
            }

    def disassociate_floating_ip(self, server_id):
        return { "floating_ip_address": "0.0.0.0" }

    def associate_floating_ip(self, server_id, external_network_id):
        return { "floating_ip_address": "0.0.0.0" }

    def create_port(self, server_id, network_id, **kwargs):
        port = kwargs
        self.all_ports.append(port)
        return port


    def find_server_ports(self, server_id):
        return self.all_ports

    def list_floating_ips(self):
        return []

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

    def list_networks(self, tenant_id=None):
        all_networks = self.all_networks
        if tenant_id is not None:
            all_networks = [ n for n in all_networks if n.get("tenant_id", "")
                    == tenant_id ]
        return all_networks

    def list_subnets(self):
        return self.all_subnets

    def list_routers(self):
        return self.all_routers

    def list_ports(self, device_id=None):
        filtered_ports = self.all_ports
        if device_id:
            filtered_ports = [ p for p in self.all_ports if
                    p.get('device_id', '') == device_id ]

        return filtered_ports

    def create_network(self, neutron, network_name):
        tenant_id = self.get_tenant_id()
        network = {
            'name': network_name,
            'admin_state_up': True,
            'id': uuid.uuid4(),
            'tenant_id': tenant_id
        }
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
        router = {'name': router_name, 'admin_state_up': True, 'external_gateway_info': { 'network_id': '' }}
        self.all_routers.append(router)
        return router

    def add_router_interface(self, router, subnet, interface_name=None):
        interface_obj = {"name": interface_name}
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


class MockAccountDriver(BaseAccountDriver):

    def __init__(self):
        self.glance_images = ALL_GLANCE_IMAGES
        self.project_name = "admin"
        self.GlanceImage = warlock.model_factory(GLANCE_IMAGE_SCHEMA)
        return

    def get_project_by_id(self, project_id):
        PROJECT_SCHEMA = {'name': {'type': ['null', 'string'], 'description': 'name of the project/tenant', 'maxLength': 255}}
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
            'file':  "/v2/images/%s/file" % identifier,
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
        for x in xrange(1, count+1):
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
