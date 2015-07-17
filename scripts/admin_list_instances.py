#!/usr/bin/env python
import argparse

from service.tasks.driver import get_idempotent_deploy_chain
from service.driver import get_esh_driver
from service.driver import get_account_driver
from core.models import Provider, Identity, Instance, InstanceStatusHistory
from core.models.instance import _get_status_name_for_provider, _convert_timestamp
import django
django.setup()

MATCH_ALL = False


def main():
    global MATCH_ALL
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-all", action="store_true",
                        help="Everything in the status-list must match")
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument(
        "--status-list",
        help="List of status to match on instances. (comma separated)")
    parser.add_argument(
        "--users",
        help="LDAP usernames to match on instances. (comma separated)")
    args = parser.parse_args()
    MATCH_ALL = args.match_all
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return
    users = args.users.split(",") if args.users else []
    print "Users Selected:%s" % users if users else "ALL USERS"

    status_list = args.status_list.split(",") if args.status_list else []
    print "Status List Selected:%s" % status_list if status_list else "ALL STATUS"

    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider
    print_instances(provider, users, status_list)


def print_instances(provider, users=[], status_list=[]):
    accounts = get_account_driver(provider)
    tenant_instances_map = accounts.tenant_instances_map(
        status_list=status_list,
        match_all=MATCH_ALL)
    for tenant, instance_list in tenant_instances_map.iteritems():
        username = tenant.name
        if users and username not in users:
            continue
        for instance in instance_list:
            instance_status = instance.extra.get('status')
            task = instance.extra.get('task')
            metadata = instance.extra.get('metadata', {})
            tmp_status = metadata.get('tmp_status', '')
            created = instance.extra.get('created', "N/A")
            updated = instance.extra.get('updated', "N/A")
            status_name = _get_status_name_for_provider(
                provider,
                instance_status,
                task,
                tmp_status)
            try:
                last_history = Instance.objects.get(
                    provider_alias=instance.id).get_last_history()
            except:
                last_history = "N/A (Instance not in this DB)"
            print "Tenant:%s Instance:%s Status: (%s - %s) Created:%s Updated:%s, Last History:%s" % (username, instance.id, instance_status, tmp_status, created, updated, last_history)

if __name__ == "__main__":
    main()
