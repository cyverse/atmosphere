#!/usr/bin/env python
"""
This script will take all users without a 'router_name' credential in Identity and assign it to them.
Distribution will occur evenly across the list in `provider.get_routers()`, and take into account previously set router_names.

NOTES:This is the only script that will (re)assign router names to identities.

      To ensure minimal disruption of user accounts, this should be performed while in 'Maintenance' with *ALL* instances shut down or suspended.

      Additionally, you will want to remove tenant networks (This will be done by default if instances are suspended/shutdown through atmosphere)

      After the routers have been re-distributed, you should be able to resume/start your instance without incident.
"""
import argparse
import django; django.setup()
from core.models import Provider, Identity
from service.monitoring import _get_instance_owner_map


def main(args):
    provider_id = args.provider
    redistribute = args.redistribute
    users = args.users.split(",")
    redistribute_routers(provider_id, users, redistribute)


def redistribute_routers(provider_id, users=[], redistribute=False):
    for provider in Provider.objects.filter(id=provider_id):
        router_map = provider.get_router_distribution()  # Print 'before'
        instance_map = _get_instance_owner_map(provider, users=users)

        if redistribute:
            needs_router = provider.identity_set.all().order_by('created_by__username')
            router_map = {key: 0 for key in router_map.keys()}
        else:
            needs_router = provider.missing_routers()

        for identity in needs_router:
            identity_user = identity.created_by.username
            if users and identity_user not in users:
                print "Skipping user %s" % identity_user
                continue
            instances = instance_map.get(identity_user, [])
            if len(instances) > 0:
                print "Skipping user %s - Reason: User has running instances" % identity_user
                continue
            # Select next available router for the identity
            selected_router = provider.select_router(router_map)
            # Save happens here:
            Identity.update_credential(identity, 'router_name', selected_router, replace=True)
            router_map[selected_router] += 1
        provider.get_router_distribution()  # Print 'after'
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Distribute router_name to all identities")
    parser.add_argument("--redistribute", action='store_true',
                        help="Provider ID to redistribute router_name.")
    parser.add_argument("--provider", dest="provider", type=int,
                        help="Provider ID to redistribute router_name.")
    parser.add_argument("--users", dest="users", type=str,
                        help="Provide a list of users (comma-separated) to limit the redistribution to that subset.")
    args = parser.parse_args()
    if not args.provider:
        parser.print_help()
    else:
        main(args)
