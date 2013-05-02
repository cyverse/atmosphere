"""
OpenStack CloudAdmin Libarary
    Use this library to:
    * manage networks within Quantum - openstack networking
"""
import os

from quantumclient.v2_0 import client as quantum_client

from atmosphere.logger import logger

from core.models.profile import get_default_subnet

class NetworkManager():

    quantum = None
    default_router = None

    def __init__(self, *args, **kwargs):
        self.default_router = kwargs.get('router_name')
        self.quantum = self.new_connection(*args, **kwargs)

    def new_connection(self, *args, **kwargs):
        """
        Allows us to make another connection (As the user)
        """
        quantum = self.connect_to_quantum(*args, **kwargs)
        return quantum

    def connect_to_quantum(self, *args, **kwargs):
        """
        """
        quantum = quantum_client.Client(*args, **kwargs)
        quantum.format = 'json'
        return quantum

    ##Admin-specific methods##
    def list_project_network(self):
        named_networks = self.find_subnet('-subnet', contains=True)
        users_with_networks = [net['name'].replace('-net','') for net in named_networks]
        return users_with_networks

    def create_project_network(self, username, password,
                              project_name, **kwargs):
        """
        This method should be run once when a new project is created
        (As the user):
        Create a network, subnet, and router
        Add interface between router and network
        (As admin):
        Add interface between router and gateway
        """
        auth_url = kwargs.get('auth_url')
        region_name = kwargs.get('region_name')
        router_name = kwargs.get('router_name')
        user_creds = {
            'username': username,
            'password': password,
            'tenant_name': project_name,
            'auth_url': auth_url,
            'region_name': region_name
        }
        logger.info("Initializing network connection for %s" % username)
        logger.info(user_creds)
        logger.info(router_name)
        user_quantum = self.new_connection(**user_creds)
        network = self.create_network(user_quantum, '%s-net' % project_name)
        subnet = self.create_user_subnet(user_quantum,
                                         '%s-subnet' % project_name,
                                         network['id'],
                                         username,
                                         get_cidr=get_default_subnet)
        public_router = self.find_router(router_name)
        if public_router:
            public_router = public_router[0]
        else:
            raise Exception("Default public router was not found.")
        #self.create_router(user_quantum, '%s-router' % project_name)
        self.add_router_interface(public_router,
                                  subnet)
        #self.set_router_gateway(user_quantum, '%s-router' % project_name)

    def delete_project_network(self, username, project_name):
        """
        remove_interface_router
        delete_subnet
        delete_network
        """
        self.remove_router_interface(self.quantum,
                                     default_router,
                                     '%s-subnet' % project_name)
        self.delete_subnet(self.quantum, '%s-subnet' % project_name)
        self.delete_network(self.quantum, '%s-net' % project_name)

    def associate_floating_ip(self, server_id):
        """
        Create a floating IP on the external network
        Find port of new VM
        Associate new floating IP with the port assigned to the new VM
        """
        external_networks = [net for net
                             in self.lc_list_networks()
                             if net.extra['router:external']]
        body = {'floatingip':
                {'floating_network_id': external_networks[0].id}}
        new_ip = self.quantum.create_floatingip(body)['floatingip']

        instance_ports = self.quantum.list_ports(device_id=server_id)['ports']
        body = {'floatingip':
                {'port_id': instance_ports[0]['id']}}
        assigned_ip = self.quantum.update_floatingip(new_ip['id'],
                                                     body)['floatingip']
        logger.info('Floating IP %s associated with instance %s'
                    % (new_ip, server_id))
        logger.info('Assigned Floating IP %s' % (assigned_ip,))
        return assigned_ip

    def find_server_ports(self, server_id):
        """
        Find all the ports for a given server_id (device_id in port object).
        """
        server_ports = []
        all_ports = self.quantum.list_ports()['ports']
        return [p for p in all_ports if p['device_id'] == server_id]

    def list_floating_ips(self):
        instance_ports = self.quantum.list_ports()['ports']
        floating_ips = self.quantum.list_floatingips()['floatingips']
        # Connect instances and floating_ips using ports.
        for fip in floating_ips:
            port = filter(lambda(p): p['id'] == fip['port_id'], instance_ports)
            if port:
                fip['instance_id'] = port[0]['device_id']
        logger.debug(floating_ips)
        return floating_ips

    ##Libcloud-Quantum Interface##
    @classmethod
    def lc_driver_init(self, lc_driver, region, *args, **kwargs):
        lc_driver_args = {
            'username': lc_driver.key,
            'password': lc_driver.secret,
            'tenant_name': lc_driver._ex_tenant_name,
            'auth_url': lc_driver._ex_force_auth_url,
            'region_name': lc_driver._ex_force_service_region}
        lc_driver_args.update(kwargs)
        manager = NetworkManager(*args, **lc_driver_args)
        return manager

    def lc_list_networks(self):
        """
        Call quantum list networks and convert to libcloud objects
        """
        network_list = self.quantum.list_networks()
        return [self._to_lc_network(net) for net in network_list['networks']]

    def _to_lc_network(self, net):
        from libcloud.compute.drivers.openstack import OpenStackNetwork
        return OpenStackNetwork(id=net['id'],
                                name=net['name'],
                                cidr=net.get('cidr', None),
                                extra=net,
                                driver=self)

    ##LOOKUP##
    def find_network(self, network_name):
        return [net for net in self.quantum.list_networks()['networks']
                if network_name == net['name']]

    def find_subnet(self, subnet_name, contains=False):
        return [net for net in self.quantum.list_subnets()['subnets']
                if subnet_name == net['name']
                or (contains and subnet_name in net['name'])]

    def find_router(self, router_name):
        return [net for net in self.quantum.list_routers()['routers']
                if router_name == net['name']]

    def find_ports(self, router_name):
        routers = self.find_router(router_name)
        if not routers:
            return []
        router_id = routers[0]['id']
        return [port for port in self.quantum.list_ports()['ports']
                if router_id == port['device_id']]

    def find_router_interface(self, router, subnet):
        if not router or not subnet:
            return None
        router_name = router['name']
        subnet_id = subnet['id']
        router_ports = self.find_ports(router_name)
        router_interfaces = []
        for port in router_ports:
            if 'router_interface' not in port['device_owner']:
                continue
            subnet_match = False
            for ip_subnet_obj in port['fixed_ips']:
                if subnet_id in ip_subnet_obj['subnet_id']:
                    subnet_match = True
                    break
            if subnet_match:
                router_interfaces.append(port)
        return router_interfaces

    def find_router_gateway(self, router_name, external_network_name='ext_net'):
        network_id = self.find_network(external_network_name)[0]['id']
        routers = self.find_router(router_name)
        if not routers:
            return
        return [r for r in routers if r.get('external_gateway_info') and
                network_id in r['external_gateway_info'].get('network_id','')]
    ##ADD##
    def create_network(self, quantum, network_name):
        existing_networks = self.find_network(network_name)
        if existing_networks:
            logger.info('Network %s already exists' % network_name)
            return existing_networks[0]

        network = {'name': network_name, 'admin_state_up': True}
        network_obj = quantum.create_network({'network': network})
        return network_obj['network']

    def create_user_subnet(self, quantum, subnet_name,
                           network_id, username,
                           ip_version=4, get_cidr=get_default_subnet):
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
                cidr = get_cidr(username, inc)
                if cidr:
                    return self.create_subnet(quantum, subnet_name,
                                              network_id, ip_version,
                                              cidr)
                else:
                    logger.warn("Unable to create cidr for subnet for user: %s")
                    inc +=1
            except Exception as e:
                logger.exception(e)
                logger.warn("Unable to create subnet for user: %s" % username)
                inc += 1
        if not success or not cidr:
            raise Exception("Unable to create subnet for user: %s" % username)

    def create_subnet(self, quantum, subnet_name,
                     network_id, ip_version=4, cidr='172.16.1.0/24'):
        existing_subnets = self.find_subnet(subnet_name)
        if existing_subnets:
            logger.info('Subnet %s already exists' % subnet_name)
            return existing_subnets[0]
        subnet = {
            'name': subnet_name,
            'network_id': network_id,
            'ip_version': ip_version,
            'cidr': cidr,
            'dns_nameservers': ['8.8.8.8', '8.8.4.4']}
        logger.debug(subnet)
        subnet_obj = quantum.create_subnet({'subnet': subnet})
        return subnet_obj['subnet']

    def create_router(self, quantum, router_name):
        existing_routers = self.find_router(router_name)
        if existing_routers:
            logger.info('Router %s already exists' % router_name)
            return existing_routers[0]
        router = {'name': router_name, 'admin_state_up': True}
        router_obj = quantum.create_router({'router': router})
        return router_obj['router']

    def add_router_interface(self, router, subnet):
        existing_router_interfaces = self.find_router_interface(router, subnet)
        if existing_router_interfaces:
            logger.info('Router Interface for Subnet:%s-Router:%s already'
                    'exists' % (subnet['name'], router['name']))
            return existing_router_interfaces[0]
        interface_obj = self.quantum.add_interface_router(
            router['id'], {
                "subnet_id": subnet['id']})
        return interface_obj

    def set_router_gateway(self, quantum, router_name,
                         external_network_name='ext_net'):
        """
        Must be run as admin
        """
        existing_gateways = self.find_router_gateway(router_name,
            external_network_name)
        if existing_gateways:
            logger.info('Router gateway for External Network:%s-Router:%s\
                already exists' % (external_network_name,router_name))
            return existing_gateways[0]
        #Establish the router_gateway
        router_id = self.get_router_id(quantum, router_name)
        external_network = self.get_network_id(quantum, external_network_name)
        body = {'network_id': external_network}
        return self.quantum.add_gateway_router(router_id, body)

    ## LOOKUPS##
    def get_subnet_id(self, quantum, subnet_name):
        sn_list = quantum.list_subnets(name=subnet_name)
        if sn_list and sn_list.get('subnets'):
            return sn_list['subnets'][0]['id']

    def get_router_id(self, quantum, router_name):
        rt_list = quantum.list_routers(name=router_name)
        if rt_list and rt_list.get('routers'):
            return rt_list['routers'][0]['id']

    def get_network_id(self, quantum, network_name):
        nw_list = quantum.list_networks(name=network_name)
        if nw_list and nw_list.get('networks'):
            return nw_list['networks'][0]['id']

    ##DELETE##
    def remove_router_gateway(self, router_name):
        router_id = self.get_router_id(self.quantum, router_name)
        if router_id:
            return self.quantum.remove_gateway_router(router_id)

    def remove_router_interface(self, quantum, router_name, subnet_name):
        router_id = self.get_router_id(quantum, router_name)
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        if router_id and subnet_id:
            try:
                return quantum\
                    .remove_interface_router(router_id,
                                             {"subnet_id": subnet_id})
            except:
                logger.error("Problem deleting interface router"
                             " from router %s to subnet %s."
                             % (router_id, subnet_id))
                raise

    def delete_router(self, quantum, router_name):
        router_id = self.get_router_id(quantum, router_name)
        if router_id:
            try:
                return quantum.delete_router(router_id)
            except:
                logger.error("Problem deleting router: %s" % router_id)
                raise

    def delete_subnet(self, quantum, subnet_name):
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        if subnet_id:
            try:
                return quantum.delete_subnet(subnet_id)
            except:
                logger.error("Problem deleting subnet: %s" % subnet_id)
                raise

    def delete_network(self, quantum, network_name):
        network_id = self.get_network_id(quantum, network_name)
        if network_id:
            try:
                return quantum.delete_network(network_id)
            except:
                logger.error("Problem deleting network: %s" % network_id)
                raise

    def delete_port(self, port):
        return self.quantum.delete_port(port['id'])

