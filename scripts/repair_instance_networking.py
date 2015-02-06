#!/usr/bin/env python
import argparse
import subprocess
import logging

try:
    from iptools.ipv4 import ip2long, long2ip
except ImportError:
    raise Exception("For this script, we need iptools. pip install iptools")

from core.models import Provider, Identity

from service.accounts.openstack import AccountDriver as OSAccountDriver
from service.driver import get_esh_driver
from service.instance import network_init

import django
django.setup()

def get_next_ip(ports):
    max_ip = -1
    for port in ports:
         fixed_ip = port['fixed_ips']
         if not fixed_ip:
             continue
         fixed_ip = fixed_ip[0]['ip_address']
         max_ip = max(max_ip, ip2long(fixed_ip))
    if max_ip <= 0:
        raise Exception("Next IP address could not be determined"
                        " (You have no existing Fixed IPs!)")
    new_fixed_ip = long2ip(max_ip + 1)
    return new_fixed_ip


def repair_instance(accounts, admin, instance, provider, new_fixed_ip=None):
    tenant_id = instance.extra['tenantId']
    tenant = accounts.user_manager.get_project_by_id(tenant_id)
    tenant_name = tenant.name
    identity = Identity.objects.get(
            created_by__username=tenant_name,
            provider__id=provider.id)
    network_init(identity)
    network_resources = accounts.network_manager.find_tenant_resources(tenant_id)
    network = network_resources['networks']
    if not network:
        network, subnet = accounts.create_network(identity)
    else:
        network = network[0]
        subnet = network_resources['subnets'][0]

    #Ensure the network,subnet exist
    if not new_fixed_ip:
        new_fixed_ip = get_next_ip(network_resources['ports'])

    user_driver = get_esh_driver(identity)
    port = accounts.network_manager.create_port(instance.id, network['id'],
            subnet['id'], new_fixed_ip, tenant_id)
    print "Created new port: %s" % port
    attached_intf = user_driver._connection.ex_attach_interface(instance.id, port['id'])
    print "Attached port to driver: %s" % attached_intf


def suspended_repair_instance(accounts, admin, instance, provider):
    try:
        old_port = instance.extra['metadata']['port-id0']
        port_id = "qbr%s" % old_port[:11]
    except (KeyError, IndexError) as exc:
        raise Exception("Instance is missing port-id0 in metadata!")
    try:
        compute_node = instance.extra['object']['OS-EXT-SRV-ATTR:host']
    except (KeyError, IndexError) as exc:
        raise Exception("Instance is missing OS-EXT-SRV-ATTR:host attribute!")

    print 'Attaching iface-bridge. Instance:%s Node:%s Port:%s'\
            % (instance.id, compute_node, port_id)
    out, err = run_command(["virsh","-c",
        "qemu+tcp://%s/system" % (compute_node,), "iface-bridge", "eth3", port_id])
    print 'Out: %s' % out
    print 'Err: %s' % err
    #Hard reboot instance


def suspended_release_instance(accounts, admin, instance, provider, port_id):
    #virsh iface-unbridge
    compute_node = instance.extra['object']['OS-EXT-SRV-ATTR:host']
    if not port_id:
        old_port = instance.extra['metadata']['port-id0']
        port_id = "qbr%s" % old_port[:11]
    elif not port_id.startswith('qbr'):
        port_id = "qbr%s" % port_id[:11]
    print 'Detaching iface-bridge. Instance:%s Node:%s Port:%s'\
            % (instance.id, compute_node, port_id)
    out, err = run_command(["virsh","-c",
        "qemu+tcp://%s/system" % (compute_node,), "iface-unbridge", port_id])
    print 'Out: %s' % out
    print 'Err: %s' % err


def run_command(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=None, dry_run=False, shell=False, bash_wrap=False,
                block_log=False):
    if bash_wrap:
        #Wrap the entire command in '/bin/bash -c',
        #This can sometimes help pesky commands
        commandList = ['/bin/bash', '-c', ' '.join(commandList)]
    """
    NOTE: Use this to run ANY system command, because its wrapped around a loggger
    Using Popen, run any command at the system level and record the output and error streams
    """
    out = None
    err = None
    cmd_str = ' '.join(commandList)
    if dry_run:
        #Bail before making the call
        logging.debug("Mock Command: %s" % cmd_str)
        return ('', '')
    try:
        if stdin:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr,
                                    stdin=subprocess.PIPE, shell=shell)
        else:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr,
                                    shell=shell)
        out, err = proc.communicate(input=stdin)
    except Exception, e:
        logging.exception(e)
    if block_log:
        #Leave before we log!
        return (out, err)
    if stdin:
        logging.debug("%s STDIN: %s" % (cmd_str, stdin))
    logging.debug("%s STDOUT: %s" % (cmd_str, out))
    logging.debug("%s STDERR: %s" % (cmd_str, err))
    return (out, err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-ip",
                        help="Fixed IP address to use "
                        " (This overrides any attempt to 'guess' "
                        "the next IP address to use.")
    parser.add_argument("--port-id",
                        help="Atmosphere port ID (Override)"
                        " to use.")
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use.")
    parser.add_argument("instance",
                        help="Instance to repair")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    parser.add_argument("--suspend-loop", action="store_true",
                        help="Repair an instance that is in suspended loop")
    parser.add_argument("--suspend-release", action="store_true",
                        help="Release the bridge-port for this instance")
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
    admin = accounts.admin_driver
    instance = admin.get_instance(instance_id)
    if not instance:
        raise Exception("Instance %s does not exist on provider %s" %
                instance_id, provider_id)
    if args.suspend_release:
        suspended_release_instance(accounts, admin, instance, provider,
                args.port_id)
    elif args.suspend_loop:
        suspended_repair_instance(accounts, admin, instance, provider)
        print 'Resuming instance: %s' % instance.id
        admin.resume_instance(instance)
        print 'Waiting 5 minutes to allow instance to resume (Ctrl+C to cancel): %s' % instance.id
        time.sleep(5*60)
        print 'Rebuilding instance network and adding port: %s' % instance.id
        repair_instance(accounts, admin, instance, provider, new_fixed_ip)
    else:
        repair_instance(accounts, admin, instance, provider, new_fixed_ip)


if __name__ == "__main__":
    main()
