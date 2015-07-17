#!/usr/bin/env python
import argparse
import sys

from service.tasks.allocation import monitor_instances_for
from core.models import Provider
import django
django.setup()


def _local_date_str_to_utc_date(end_date_str, timezone="America/Phoenix"):
    import pytz
    from datetime import datetime
    if not end_date_str:
        return None
    local = pytz.timezone(timezone)
    naive_end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
    local_end_date = local.localize(naive_end_date, is_dst=None)
    end_date = local_end_date.astimezone(pytz.utc)
    return end_date


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
    parser.add_argument(
        "--end",
        help="End date to use for monitoring. Expects Log formatting: YYYY-MM-DD HH:MM:SS")
    args = parser.parse_args()
    openstack_prov = Provider.objects.get(id=args.provider_id)
    users = args.users.split(',') if args.users else None
    if not args.end:
        end_date = None
    try:
        end_date = _local_date_str_to_utc_date(args.end)
    except ValueError as bad_format:
        print >> sys.stderr, "ERROR: End date '%s'"\
            " does not match Expected format: 'YYYY-MM-DD HH:MM:SS'"
        return 1
    monitor_instances_for(openstack_prov.id, users=users,
                          print_logs=True, end_date=end_date)

if __name__ == "__main__":
    main()
