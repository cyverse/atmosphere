import os

from quantumclient.v2_0 import client as quantum_client
from novaclient.v1_1 import client as nova_client

from atmosphere.logger import logger
from atmosphere import settings

import os
"""
OpenStack CloudAdmin Libarary
    Use this library to:
    * manage networks within Quantum - openstack networking 
  
For each usergroup:

"""

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
        self.quantum = self.newConnection(*args, **kwargs)#username,password,tenant_name,auth_url)

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
        create-network TestTenant-Net 
        subnet_id = Create subnet TestTenant-Net 172.16.1.0/24 
        create a router TestTenant-R1
        add the router's interface to the tenant subnet TestTenant-R1 ${tenant_subnet_id}
        setup the tenant's gateway TestTenant-R1 ext_net
        """
        user_creds = {
            'username': username, 
            'password': password, 
            'tenant_name': tenant_name,
            'auth_url': settings.OPENSTACK_ADMIN_URL,
            'region_name': settings.OPENSTACK_DEFAULT_REGION
        }
        user_quantum = newConnection(**user_creds)
        network_obj = self.createNetwork(quantum, '%s-net' % username)
        subnet_obj = self.createSubnet(quantum, '%s-subnet' % username, '%s-net' % username)
        router_obj = self.createRouter(quantum, '%s-router' % username, tenant_id)
        interface_obj = self.addRouterInterface(quantum, '%s-router' % username, '%s-subnet' % username)
        gateway_obj = self.setRouterGateway(quantum, router_name, network)

    def deleteTenantNetwork(self, username, tenant_name):
        """
        TODO: test when necessary:
        remove_gateway_router
        remove_interface_router
        delete_router
        delete_subnet
        delete_network
        """
        gateway_obj = self.removeRouterGateway(router_name, network)
        interface_obj = self.removeRouterInterface(quantum, '%s-router' % username, '%s-subnet' % username)
        router_obj = self.deleteRouter(quantum, '%s-router' % username, tenant_id)
        subnet_obj = self.deleteSubnet(quantum, '%s-subnet' % username, '%s-net' % username)
        network_obj = self.deleteNetwork(quantum, '%s-net' % username)

    def associate_floating_ip(self):
        """
        Get VM Port ID
        Associate Floating IP to VM Port ID
        ===
        ip_id = floatingip-create ext-net
        vm_port_id = port-list device-id=tenant_vm
        floatingip-associate ip_id vm_port_id
        """
        external_networks = [net for net in self.lc_list_networks() if net.extra['router:external']]
        new_floating_ip = self.quantum.create_floatingip({'floatingip':{'floating_network_id':external_network[0].id}})['floatingip']
        instance_ports = self.quantum.list_ports(device_id='3c7b58b6-d479-4b79-8ae1-aef1b2aabc45')['ports']
        associated_floating_ip = self.quantum.update_floatingip(new_floating_ip['id'], {'floatingip':{'port_id':instance_ports[0]['id']}})



    
    ##Libcloud-Quantum Interface##
    @classmethod
    def lc_driver_init(self, lc_driver, region=None, *args, **kwargs):
        lc_driver_args = {
        'username':lc_driver.key,
		'password':lc_driver.secret,
		'tenant_name':lc_driver._ex_tenant_name,
		'auth_url':lc_driver._ex_force_auth_url,
		'region_name':region if region else settings.OPENSTACK_DEFAULT_REGION
        }
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
                                extra = net,
                                driver=self)

    ##ADD##
    def createNetwork(self, quantum, network_name):
        network = {'name': network_name, 'admin_state_up': True}
        network_obj = quantum.create_network({'network':network})
        return network_obj

    def createSubnet(self, quantum, subnet_name, network_id, ip_version=4, cidr='172.16.1.0/24'):
        subnet = {'name':subnet_name, 
            'network_id': network_id, 
            'ip_version':ip_version, 
            'cidr':cidr, 
            }
        subnet_obj = quantum.create_subnet({'subnet':subnet})
        return subnet_obj

    def createRouter(self, quantum, router_name):
        router = {'name': router_name, 'admin_state_up': True}
        router_obj = quantum.create_router({'router':router})
        return router_obj

    def addRouterInterface(self, quantum, router_name, subnet_name):
        router_id = self.get_router_id(quantum, router_name)
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        interface_obj = quantum.add_interface_router(router_id, {"subnet_id": subnet_id})
        return interface_obj

    def setRouterGateway(self, quantum, router_name, external_network_name='ext_net'):
        """
        Must be run as admin
        """
        router_id = self.get_router_id(quantum, router_name)
        external_network = self.get_network_id(quantum, external_network_name)
        return self.quantum.add_gateway_router(router_id, {'network_id': external_network})

    ## LOOKUPS##
    def get_subnet_id(self, quantum, subnet_name):
        sn_list = quantum.list_networks(name=subnet_name)
        return sn_list['subnets'][0]['id']

    def get_router_id(self, quantum, router_name):
        rt_list = quantum.list_routers(name=router_name)
        return rt_list['routers'][0]['id']

    def get_network_id(self, quantum, network_name):
        nw_list = quantum.list_networks(name=network_name)
        return nw_list['networks'][0]['id']

    ##DELETE##
    def removeRouterGateway(router_name, external_network_name):
        router_id = self.get_router_id(quantum, router_name)
        external_network = self.get_network_id(quantum, external_network_name)
        return self.quantum.remove_gateway_router(router_id, {'network_id': external_network})

    def removeRouterInterface(quantum, router_name, subnet_name):
        router_id = self.get_router_id(quantum, router_name)
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        return quantum.remove_interface_router(router_id, {"subnet_id": subnet_id})

    def deleteRouter(quantum, router_name):
        router_id = self.get_router_id(quantum, router_name)
        return quantum.delete_router(router_id)

    def deleteSubnet(quantum, subnet_name):
        subnet_id = self.get_subnet_id(quantum, subnet_name)
        return quantum.delete_subnet(subnet_id)

    def deleteNetwork(quantum, network_name):
        network_id = self.get_network_id(quantum, network_name)
        return quantum.delete_network(network_id)

"""
Utility Functions
"""
def test():
    manager = NetworkManager.settings_init()

    manager.createTenantNetwork('username','password','tenant_name')
    print "Created test usergroup"
    manager.deleteTenantNetwork('username')
    print "Deleted test usergroup"

if __name__ == "__main__":
    test()
