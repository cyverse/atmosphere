#!/usr/bin/env python
import argparse
import time

from service.driver import get_esh_driver
from core.models import Provider, Identity, Instance, InstanceStatusHistory
from service.driver import get_admin_driver
from service.instance import suspend_instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    args = parser.parse_args()
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return
    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider
    user_instances = get_user_instance_history(provider)
    admin_driver = get_admin_driver(provider)
    all_instances = admin_driver.list_all_instances()
    prune_history(user_instances, all_instances)

def prune_history(user_instances, all_instances):
    """
    1. for username in keys
    2. get list of instances we think exist
    3. if instance not in that list, end date all
    1. 
    """
    for username in user_instances.keys():
        instance_ids = user_instances[username]
        for instance_id in instance_ids:
            instance_exists = any(instance for instance in all_instances if instance.id == instance_id)
            if instance_exists:
                continue
            core_instance = Instance.objects.get(provider_alias=instance_id)
            bad_history_list = core_instance.instancestatushistory_set.filter(
                          end_date__isnull=True)
            print "%s Instance %s does NOT exist. Pruning %s events: %s"\
                          % (username, instance_id, bad_history_list.count(), bad_history_list)
            _prune_history(bad_history_list)

def _prune_history(bad_history_list):
    for history in bad_history_list:
        history.end_date = history.start_date
        history.save()
            

def get_user_instance_history(provider):
    user_instances = {}
    all_history = InstanceStatusHistory.objects.filter(end_date__isnull=True, instance__source__providermachine__provider=provider)
    for history in all_history:
        username = history.instance.created_by.username
        a_set = user_instances.get(username,set())
        a_set.add(history.instance.provider_alias)
        user_instances[username] = a_set
    return user_instances



if __name__ == "__main__":
    main()
