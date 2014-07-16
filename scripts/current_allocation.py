#!/usr/bin/env python
import argparse

from service.tasks.allocation import monitor_instances_for
from core.models import Provider

def main():
    """
    Add a user to openstack.
    """
    errors = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-id", type=int, required=True,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    args = parser.parse_args()
    openstack_prov = Provider.objects.get(id=args.provider_id)
    users = args.users.split(',') if args.users else None
    monitor_instances_for(openstack_prov, users=users, print_logs=True)

if __name__ == "__main__":
    main()

