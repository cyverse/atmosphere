#!/usr/bin/env python
import argparse
import time

from collections import OrderedDict
from core.models import Provider, Identity
from service.driver import get_admin_driver, get_esh_driver
from service.instance import suspend_instance, stop_instance
import django
django.setup()
SLEEP_MIN=30
SLEEP_MAX=2*60

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--action",
                        help="Atmosphere Action to take [Suspend/Stop]")
    parser.add_argument("--sleep",
                        help="# of seconds to sleep after taking action")
    parser.add_argument("--dry-run", action="store_true",
                        help="A 'dry-run' so you know what will happen,"
                             " before it happens")
    args = parser.parse_args()
    dry_run = args.dry_run
    sleep_time = args.sleep
    action = "suspend"
    provider = None
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    #Debugging args
    if dry_run:
        print "Dry run initialized.."

    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return
    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider

    if args.action and 'stop' in args.action.lower():
        action = 'stop'
        print "Begin stopping Instances"
    else:
        print "Begin suspending Instances"
    suspend_all_instances(provider, action, sleep_time, dry_run)


def suspend_all_instances(provider, action, sleep_time=None, dry_run=False):
    admin_driver = get_admin_driver(provider)
    all_insts = admin_driver.meta(admin_driver=admin_driver).all_instances()
    users = []
    bad_instances = []
    for i in all_insts:
        if 'creator' in i.extra['metadata']:
            users.append(i.extra['metadata']['creator'])
        else:
            bad_instances.append(i)
    if bad_instances:
        print "WARN: These instances are MISSING because they have incomplete metadata:\n%s" % (bad_instances,)
    all_users = sorted(list(OrderedDict.fromkeys(users)))
    for count, user in enumerate(all_users):
        ident = Identity.objects.filter(created_by__username=user, provider__id=4)
        if len(ident) > 1:
            print "WARN: User %s has >1 identity!" % user
        ident = ident[0]
        driver = get_esh_driver(ident)
        instances = driver.list_instances()
        print "Found %s instances for %s" % (len(instances), user)
        for inst in instances:
            if not sleep_time:
                sleep_for = random.uniform(SLEEP_MIN,SLEEP_MAX)
            else:
                sleep_for = sleep_time
            _execute_action(ident, inst, action, sleep_for, dry_run)

def _execute_action(ident, inst, action, sleep_time, dry_run=False):
    status = inst._node.extra['status']
    if status != 'active':
        print "Skipping instance %s in state %s" % (inst.id, status)
    if 'suspend' in action.lower():
        _execute_suspend(ident, inst, status, sleep_time, dry_run)
    elif 'stop' in action.lower():
        _execute_stop(ident, inst, status, sleep_time, dry_run)
    else:
        raise Exception("Unknown Action : %s" % action)

def _execute_stop(ident, inst, status, sleep_time, dry_run=False):
    if status == 'active':
        print "Attempt to Stop Instance %s in state %s" % (inst.id, status)
        try:
            if not dry_run:
                stop_instance(driver, inst, ident.provider.id, ident.id, ident.created_by)
            print "Shutoff Instance %s.. Sleep %s seconds" % (inst.id,sleep_time)
            if not dry_run:
                time.sleep(sleep_time)
        except Exception, err:
            print "WARN: Could not shut off instance %s. Original Status:%s Error: %s" % (inst.id, status, err)

def _execute_suspend(ident, inst, status, sleep_time, dry_run=False):
    if status == 'active':
        print "Attempt to suspend Instance %s in state %s" % (inst.id, inst._node.extra['status'])
        try:
            if not dry_run:
                suspend_instance(driver, inst, ident.provider.id, ident.id, ident.created_by)
            print "Suspended Instance %s.. Sleep %s seconds" % (inst.id,sleep_time)
            if not dry_run:
                time.sleep(sleep_time)
        except Exception, err:
            print "WARN: Could not suspend instance %s. Original Status:%s Error: %s" % (inst.id, status, err)

if __name__ == "__main__":
    main()
