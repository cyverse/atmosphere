#!/usr/bin/env python
import argparse
import time

from service.tasks.driver import get_idempotent_deploy_chain
from service.driver import get_esh_driver
from service.driver import get_account_driver
from core.models import Provider, Identity

import django
django.setup()

DO_NOTHING = False

def main():
    global DO_NOTHING
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    args = parser.parse_args()
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    if args.dry_run:
        DO_NOTHING = True
    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return
    users = args.users.split(",") if args.users else []
    print "Users Selected:%s" % users if users else "ALL AFFECTED"

    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider
    accounts = get_account_driver(provider)
    admin_driver = accounts.admin_driver
    all_instances = admin_driver.list_all_instances()
    tenant_id_map = accounts._make_tenant_id_map()
    redeploy_users(provider, all_instances, tenant_id_map, users)

def redeploy_users(provider, all_instances, tenant_id_map, users=[]):
    for instance in all_instances:
       metadata = instance._node.extra.get('metadata',{})
       instance_status = instance.extra.get('status')
       tmp_status = metadata.get('tmp_status','')
       username = metadata.get('creator','')
       if not metadata:
           print "WARN: Instance %s has NO metadata!" % instance.id
           continue
       if not username:
           tenant_id = instance.extra.get('tenantId')
           username = tenant_id_map[tenant_id]
       if not username:
           print "WARN: Instance %s Metadata MISSING a username AND tenantID!: %s" % (instance.id, metadata)
           continue
       if tmp_status not in ['deploy_error', 'networking','deploying','initializing']:
           continue
       if instance_status not in ['build','active']:
           continue
       if users and username not in users:
           print "Found affected user:%s and Instance:%s - Skipping because they aren't in the list." % (username, instance.id)
           continue
       print "Starting idempotent redeployment for %s - Instance: %s (%s - %s)" % (username, instance.id, instance_status, tmp_status)
       ident = Identity.objects.get(provider=provider, created_by__username=username)
       driver = get_esh_driver(ident)
       start_task = get_idempotent_deploy_chain(driver.__class__, driver.provider, driver.identity, instance, username)
       print "Starting idempotent redeployment: %s ..." % (start_task),
       if DO_NOTHING:
           continue
       start_task.apply_async()
       print " Sent"
       

if __name__ == "__main__":
    main()
