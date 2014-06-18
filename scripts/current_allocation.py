#!/usr/bin/env python
import argparse

from core.models import Provider, Identity
from service.accounts.openstack import AccountDriver
from service.tasks.allocation import get_instance_owner_map
from service.allocation import get_allocation, get_time
from api import get_esh_driver
from datetime import timedelta

def main():
    """
    Add a user to openstack.
    """
    errors = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int, required=True,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    args = parser.parse_args()
    openstack_prov = Provider.objects.get(id=args.provider)
    accounts = AccountDriver(openstack_prov)
    size_map = dict( (size.id, size) for size in
            accounts.admin_driver.list_sizes())
    username_inst_map = get_instance_owner_map(openstack_prov)
    success = 0
    #Sort by username
    #user_list = sorted(username_inst_map.keys())
    #Sort by # of instances
    user_list = sorted(username_inst_map,
                       key=lambda key: len(username_inst_map[key]),
                       reverse=True)
    if args.users:
        arg_users = args.users.split(',')
        #Prune
        user_list = [user for user in user_list if user in arg_users]
        #Look for missing
        for user in arg_users:
            if user not in user_list:
                print "WARN: User %s does not have an identity on Provider %s"\
                      % (user, openstack_prov)
    for username in user_list:
        print "%s, " % (username,),
        identity = Identity.objects.filter(provider=openstack_prov,
                                        created_by__username=username)
        if not identity:
            print " SKIPPED. See errors below."
            errors.append("User %s does not have an identity on Provider %s"\
                  % (username, openstack_prov))
            continue
        elif len(identity) > 1:
            print " SKIPPED. See errors below."
            errors.append("User %s has MULTIPLE identities on Provider %s"\
                  % (username, openstack_prov))
            continue
        identity = identity[0]
        instances = username_inst_map[username]
        allocation = get_allocation(username, identity.id)
        if allocation:
            max_time_allowed = timedelta(minutes=allocation.threshold)
            total_time_used = get_time(
                    identity.created_by, identity.id, allocation.delta)
            time_diff = max_time_allowed - total_time_used
            print "Used: %s , Allowed: %s, Remaining: %s"\
                    % (total_time_used, max_time_allowed, time_diff)
        else:
            print "Used: N/A, Allowed: N/A, Remaining: No Allocation"
        if instances:
            print "Instances: %s" % pprint_instances(instances, size_map)
    if errors:
        print "ERRORS BELOW:"
        for error in errors:
            print error

def pprint_instances(instances, size_map):
    instance_str = "\n\t#\tInstance\t\t\t\tStatus\tSize\n"
    for idx, inst in enumerate(instances):
        #Convert from MockSize (id only) --> OSSize (Detailed)
        os_size = size_map[inst.size.id]
        instance_str += "\t%s\t%s\t%s\t%s\n" % (idx, inst.alias, inst.extra['status'], os_size.name)
    return instance_str

if __name__ == "__main__":
    main()

