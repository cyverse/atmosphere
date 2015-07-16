#!/usr/bin/env python
import argparse
from django.conf import settings
from service.allocation import core_instance_time, get_delta, get_allocation
from django.utils import timezone
from core.models import Provider, Identity
import django
django.setup()


def check_usernames(provider_id, usernames):
    for username in usernames:
        ident = Identity.objects.get(
            provider__id=provider_id,
            created_by__username=username)
        print "Provider: %s - Username: %s" % (ident.provider, ident.created_by.username)
        total_time, instances_map = core_instance_time(
            ident.created_by, ident.id,
            get_delta(
                get_allocation(ident.created_by.username, ident.id),
                settings.FIXED_WINDOW, timezone.now()),
            [],
            now_time=timezone.now())
        instance_list = instances_map.keys()
        for instance in instance_list:
            print "Instance:%s Time Used:%s" % (instance.provider_alias, instance.active_time)
            for history in instances_map[instance]:
                if history.cpu_time > timezone.timedelta(0):
                    print "Status:%s %s*(%s - %s) = %s" % (history.status.name, history.size.cpu, history.start_date, history.end_date, history.cpu_time)
        print "Total Time Given:%s Total time used: %s" % (timezone.timedelta(minutes=get_allocation(ident.created_by.username, ident.id).threshold), total_time)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    args = parser.parse_args()
    users = None
    quota = None
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
    check_usernames(int(args.provider_id), users)

if __name__ == "__main__":
    main()
