#!/usr/bin/env python
import argparse
import time

from core.models import Provider, Identity
from service.driver import get_account_driver, get_esh_driver
from service.instance import suspend_instance, stop_instance
import django
django.setup()
SLEEP_MIN = 30


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument(
        "--users",
        type=str,
        help="List of Users to take action on (Comma-separated)."
        " (Default: All Users)")
    parser.add_argument("--action",
                        help="Atmosphere Action to take [Suspend/Stop/Shelve]"
                        " (Default:Suspend)")
    parser.add_argument("--sleep", type=int,
                        help="# of seconds to sleep after taking action"
                        " (Default:30sec)")
    parser.add_argument("--dry-run", action="store_true",
                        help="A 'dry-run' so you know what will happen,"
                             " before it happens")
    args = parser.parse_args()

    users = []
    action = None
    provider = None
    sleep_time = None
    # Parsed Args
    dry_run = args.dry_run
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    if args.sleep:
        sleep_time = args.sleep
    else:
        sleep_time = SLEEP_MIN
    if args.users:
        users = args.users.split(",")
    else:
        users = []
    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return
    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider

    if not args.action:
        action = "suspend"
    else:
        action = args.action.lower()
    start_instance_maintenances(provider, action, users, sleep_time, dry_run)


def _create_hostname_mapping(all_instances):
    host_map = {}
    for inst in all_instances:
        key = inst.extra['object']['OS-EXT-SRV-ATTR:hypervisor_hostname']
        if not key:
            print "Skipping Instance %s - not on a host" % inst.id
            continue
        inst_list = host_map.get(key, [])
        inst_list.append(inst)
        host_map[key] = inst_list
    return host_map


def make_user_instances(instance_list, all_tenants, users):
    """
    Filters users not in 'the list of users'
    Adds a temporary 'username' attribute to avoid future lookups.
    """
    new_list = []
    for instance in instance_list:
        tenantId = instance.owner
        tenant = [user for user in all_tenants if user.id == tenantId]
        if not tenant:
            print "Missing tenant information on instance %s" % instance.id
            continue
        username = tenant[0].name
        if users and username not in users:
            continue
        # NOTE: creates a new 'temp attr' .username
        instance.username = username
        new_list.append(instance)
    return new_list


def start_instance_maintenances(
        provider,
        action,
        users=[],
        sleep_time=None,
        dry_run=False):
    accounts = get_account_driver(provider)
    all_insts = accounts.list_all_instances()
    all_tenants = accounts.list_projects()
    all_insts = make_user_instances(all_insts, all_tenants, users)
    hostname_map = _create_hostname_mapping(all_insts)
    finished = False
    while not finished:
        # Iterate the list of hosts, complete
        finished = True
        for host in hostname_map.keys():
            inst_list = hostname_map[host]
            if len(inst_list) == 0:
                continue
            instance = inst_list.pop()
            print "Instance %s - Hostname %s" % (instance.id, host)
            status = instance.extra['status']
            if status != 'active':
                print "Skipping instance %s in state %s" % (instance.id, status)
                continue
            finished = False
            identity = Identity.objects.get(
                created_by__username=instance.username,
                provider=provider)
            print 'Performing Instance Maintenance - %s - %s' % (instance.id, host)
            try:
                _execute_action(identity, instance, action, dry_run)
            except Exception as e:
                print "Could not %s Instance %s - Error %s" % (action, instance.id, e)
                continue
        print "Waiting %s seconds" % sleep_time
        if not dry_run:
            time.sleep(sleep_time)


def _execute_action(identity, instance, action, dry_run=False):
    driver = get_esh_driver(identity)
    if action == 'stop':
        if not dry_run:
            stop_instance(
                driver,
                instance,
                identity.provider.id,
                identity.id,
                identity.created_by)
        print "Shutoff instanceance %s" % (instance.id,)
    elif action == 'suspend':
        print "Attempt to suspend instanceance %s in state %s" % (instance.id, instance._node.extra['status'])
        if not dry_run:
            suspend_instance(
                driver,
                instance,
                identity.provider.id,
                identity.id,
                identity.created_by)
        print "Suspended instanceance %s" % (instance.id)

if __name__ == "__main__":
    main()
