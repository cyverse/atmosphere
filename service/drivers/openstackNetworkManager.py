"""
OpenStack CloudAdmin Libarary
    Use this library to:
    * manage networks within Quantum - openstack networking
"""
import os

from quantumclient.v2_0 import client as quantum_client

from atmosphere import settings
from atmosphere.logger import logger


class NetworkManager():

    quantum = None

    @classmethod
    def settings_init(self, *args, **kwargs):
        settings_args = {
            'username': settings.OPENSTACK_ADMIN_KEY,
            'password': settings.OPENSTACK_ADMIN_SECRET,
            'tenant_name': settings.OPENSTACK_ADMIN_TENANT,
            'auth_url': settings.OPENSTACK_ADMIN_URL,
            'region_name': settings.OPENSTACK_DEFAULT_REGION
        }
        settings_args.update(kwargs)
        manager = NetworkManager(*args, **settings_args)
        return manager

    def __init__(self, *args, **kwargs):
        self.quantum = self.newConnection(*args, **kwargs)

    def newConnection(self, *args, **kwargs):
        """
        Allows us to make another connection (As the user)
        """
        quantum = quantum_client.Client(*args, **kwargs)
        quantum.format = 'json'
        return quantum

    ##Admin-specific methods##
    def createTenantNetwork(self, username, password, tenant_name, tenant_id):
        """
        This method should be run once when a new tenant is created
        (As the user):
        Create a network, subnet, and router
        Add interface between router and network
        (As admin):
        Add interface between router and gateway
        """
        user_creds = {
            'username': username,
            'password': password,
            'tenant_name': tenant_name,
            'auth_url': settings.OPENSTACK_ADMIN_URL,
            'region_name': settings.OPENSTACK_DEFAULT_REGION
        }
        user_quantum = self.newConnection(**user_creds)
        network = self.createNetwork(user_quantum, '%s-net' % tenant_name)
        subnet = self.createSubnet(user_quantum,
                                   '%s-subnet' % tenant_name,
                                   network['id'])
        router = self.createRouter(user_quantum, '%s-router' % tenant_name)
        self.addRouterInterface(user_quantum,
                                '%s-router' % tenant_name,
                                '%s-subnet' % tenant_name)
        self.setRouterGateway(user_quantum, '%s-router' % tenant_name)

    def deleteTenantNetwork(self, username, tenant_name):
        """
        TODO: test when necessary:
        remove_gateway_router
        remove_interface_router
        delete_router
        delete_subnet
        delete_network
        """
        self.removeRouterGateway('%s-router' % tenant_name)
        self.removeRouterInterface(self.quantum,
                                   '%s-router' % tenant_name,
                                   '%s-subnet' % tenant_name)
        self.deleteRouter(self.quantum, '%s-router' % tenant_name)
        self.deleteSubnet(self.quantum, '%s-subnet' % tenant_name)
        self.deleteNetwork(self.quantum, '%s-net' % tenant_name)

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
        assigned_ip = self.quantum.update_floatingip(new_ip['id'], body)
        logger.info('Floating IP %s associated with instance %s'
                    % (new_ip, server_id))
        return assigned_ip

    ##Libcloud-Quantum Interface##
    @classmethod
    def lc_driver_init(self, lc_driver, region=None, *args, **kwargs):
        if not region:
            region = settings.OPENSTACK_DEFAULT_REGION

        lc_driver_args = {
            'username': lc_driver.key,
            'password': lc_driver.secret,
            'tenant_name': lc_driver._ex_tenant_name,
            'auth_url': lc_driver._ex_force_auth_url,
            'region_name': region}
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

    ##ADD##
    def createNetwork(self, quantum, network_name):
        network = {'name': network_name, 'admin_state_up': True}
        network_obj = quantum.create_network({'network': network})
        return network_obj['network']

    def createSubnet(self, quantum, subnet_name,
                     network_id, ip_version=4, cidr='172.16.1.0/24'):
        subnet = {
            'name': subnet_name,
            'network_id': network_id,
            'ip_version': ip_version,
            'cidr': cidr,
            'dns_nameservers': ['8.8.8.8', '8.8.4.4']}
        logger.debug(subnet)
        subnet_obj = quantum.create_subnet({'subnet': subnet})
        return subnet_obj['subnet']

    def createRouter(self, quantum, router_name):
        router = {'name': router_name, 'admin_state_up': True}
        router_obj = quantum.create_router({'router': router})
        return router_obj['router']

    def addRouterInterface(self, quantum, router_name, subnet_name):
        router_id = self.get_router_id(quantum, router_name)
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        interface_obj = quantum.add_interface_router(router_id, {
            "subnet_id": subnet_id})
        return interface_obj

    def setRouterGateway(self, quantum, router_name,
                         external_network_name='ext_net'):
        """
        Must be run as admin
        """
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
    def removeRouterGateway(self, router_name):
        router_id = self.get_router_id(self.quantum, router_name)
        if router_id:
            return self.quantum.remove_gateway_router(router_id)

    def removeRouterInterface(self, quantum, router_name, subnet_name):
        router_id = self.get_router_id(quantum, router_name)
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        if router_id and subnet_id:
            try:
                return quantum\
                    .remove_interface_router(router_id,
                                             {"subnet_id": subnet_id})
            except:
                logger.debug("Problem deleting interface router"
                             " from router %s to subnet %s."
                             % (router_id, subnet_id))

    def deleteRouter(self, quantum, router_name):
        router_id = self.get_router_id(quantum, router_name)
        if router_id:
            try:
                return quantum.delete_router(router_id)
            except:
                logger.debug("Problem deleting router: %s" % router_id)

    def deleteSubnet(self, quantum, subnet_name):
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        if subnet_id:
            try:
                return quantum.delete_subnet(subnet_id)
            except:
                logger.debug("Problem deleting subnet: %s" % subnet_id)

    def deleteNetwork(self, quantum, network_name):
        network_id = self.get_network_id(quantum, network_name)
        if network_id:
            try:
                return quantum.delete_network(network_id)
            except:
                logger.debug("Problem deleting network: %s" % network_id)


def test():
    manager = NetworkManager.settings_init()

    manager.createTenantNetwork('username', 'password', 'tenant_name')
    print "Created test usergroup"
    manager.deleteTenantNetwork('username')
    print "Deleted test usergroup"

if __name__ == "__main__":
    test()
