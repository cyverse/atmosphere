#!/usr/bin/env python
import argparse

from service.accounts.openstack import AccountDriver as OSAccountDriver
from api import get_esh_driver
from core.models import Provider, Identity

try:
    from iptools.ipv4 import ip2long, long2ip
except ImportError:
    raise Exception("For this script, we need iptools. pip install iptools")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-ip",
                        help="Fixed IP address to use "
                        " (This overrides any attempt to 'guess' "
                        "the next IP address to use.")
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use.")
    parser.add_argument("instance",
                        help="Instance to repair")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    args = parser.parse_args()
    users = None
    added = 0
    provider_id = args.provider
    instance_id = args.instance
    new_fixed_ip = args.fixed_ip
    if not provider_id:
        provider_id = 4
    if not instance_id:
        raise Exception("Instance ID is required")
    provider = Provider.objects.get(id=provider_id)

    accounts = OSAccountDriver(Provider.objects.get(id=provider_id))
    instance = accounts.admin_driver.get_instance(instance_id)
    if not instance:
        raise Exception("Instance %s does not exist on provider %s" %
                instance_id, provider_id)
    tenant_id = instance.extra['tenantId']
    tenant = accounts.user_manager.get_project_by_id(tenant_id)
    tenant_name = tenant.name
    identity = Identity.objects.get(
            created_by__username=tenant_name,
            provider__id=provider_id)
    network_resources = accounts.network_manager.find_tenant_resources(tenant_id)
    network = network_resources['networks']
    if not network:
        network, subnet = accounts.create_network(identity)
    else:
        network = network[0]
        subnet = network_resources['subnets'][0]
    user_driver = get_esh_driver(identity)
    max_ip = -1
    for port in network_resources['ports']:
        fixed_ip = port['fixed_ips']
        if not fixed_ip:
            continue
        fixed_ip = fixed_ip[0]['ip_address']
        max_ip = max(max_ip, ip2long(fixed_ip))
    if max_ip <= 0:
        raise Exception("Next IP address could not be determined"
                        " (You have no existing Fixed IPs!)")
    new_fixed_ip = long2ip(max_ip + 1)
    port = accounts.network_manager.create_port(instance_id, network['id'],
            subnet['id'], new_fixed_ip, tenant_id)
    print "Created new port: %s" % port
    attached_intf = user_driver._connection.ex_attach_interface(instance_id, port['id'])
    print "Attached port to driver: %s" % attached_intf

if __name__ == "__main__":
    main()
