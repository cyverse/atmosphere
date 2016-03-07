#!/usr/bin/env python
import argparse

import django
django.setup()

from service.tasks.driver import get_idempotent_deploy_chain
from service.driver import get_esh_driver
from service.driver import get_account_driver
from core.models import Provider, Identity, Instance

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
    redeploy_users(provider, users)


def redeploy_users(provider, users=[]):
    accounts = get_account_driver(provider)
    tenant_instances_map = accounts.tenant_instances_map(
        status_list=[
            'deploy_error',
            'networking',
            'deploying',
            'initializing'])
    for tenant, instance_list in tenant_instances_map.iteritems():
        username = tenant.name
        if users and username not in users:
            print "Found affected user:%s and Instances:%s - Skipping because they aren't in the list." % (username, instance_list)
            continue
        for instance in instance_list:
            metadata = instance._node.extra.get('metadata', {})
            instance_status = instance.extra.get('status')
            tmp_status = metadata.get('tmp_status', '')
            print "Starting idempotent redeployment for %s - Instance: %s (%s - %s)" % (username, instance.id, instance_status, tmp_status)
            ident = Identity.objects.get(
                provider=provider,
                created_by__username=username)
            driver = get_esh_driver(ident)
            try:
                start_task = get_idempotent_deploy_chain(
                    driver.__class__,
                    driver.provider,
                    driver.identity,
                    instance,
                    username)
                print "Starting idempotent redeployment: %s ..." % (start_task),
                start_task.apply_async()
            except Identity.DoesNotExist:
                print "Identity does not exist in this DB. SKIPPED."
                continue
            if DO_NOTHING:
                continue
            print " Sent"


if __name__ == "__main__":
    main()
