#!/usr/bin/env python
import argparse
import requests
import time

import libcloud.security

from threepio import logger

from authentication.protocol.ldap import is_atmo_user, get_members

from core.models import AtmosphereUser as User
from core.models import Provider, Quota

from service.driver import get_account_driver


libcloud.security.VERIFY_SSL_CERT = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--quota-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--quota-id",
                        help="Atmosphere Quota ID to assign (Optional)")
    parser.add_argument("--groups",
                        help="LDAP groups to import. (comma separated)")
    parser.add_argument("--dry-run", action="store_true",
                        help="A 'dry-run' so you know what will happen,"
                             " before it happens")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    parser.add_argument("--admin", action="store_true",
                        help="ALL Users addded are treated as admin and staff "
                        "users. They also receive the maximum quota.")
    args = parser.parse_args()
    make_admins = args.admin
    dry_run = args.dry_run
    users = None
    quota = None
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    elif args.quota_list:
        print "ID\tSpecs"
        for q in Quota.objects.all().order_by('id'):
            print "%s\t%s" % (q.id, q)
        return

    #Debugging args
    if dry_run:
        print "Dry run initialized.."

    #Optional args
    if args.quota_id:
        quota = Quota.objects.get(id=args.quota_id)

    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider

    acct_driver = get_account_driver(provider)

    groups = args.groups.split(",") if args.groups else []
    total_added = process_groups(acct_driver, groups, quota, make_admins)

    users = args.users.split(",") if args.users else []
    total_added += process_users(acct_driver, users, quota, make_admins)

    print "Processing complete. %d users processed." % total_added


def process_groups(acct_driver, groups, quota=None, make_admin=False):
    total_added = 0
    for groupname in groups:
        group_add = 0
        users = get_members(groupname)
        print "Total users in group %s:%s" % (groupname, len(users))
        group_add = process_users(acct_driver, users, quota, make_admin)
        total_added += group_add
    return total_added


def process_users(acct_driver, users, quota=None, admin_user=False):
    total_added = 0
    for user in users:
        success = process_user(acct_driver, user, quota=quota,
                               admin_user=admin_user)
        if success:
            total_added += 1
    print "Total users added:%s" % (total_added)
    return total_added


def process_user(acct_driver, username, quota=None, admin_user=False):
    try:
        if not is_atmo_user(username):
            print "%s is not in the LDAP atmosphere group (atmo-user)." %\
                (username)
            return False
        if not dry_run:
            acct_driver.create_account(username,
                                       quota=quota,
                                       # Admin users get maximum quota
                                       max_quota=admin_user)
        if admin_user:
            if not dry_run:
                make_admin(username)
            print "%s added as admin." % (username)
        else:
            print "%s added." % (username)
        return True
    except Exception as e:
        print "Problem adding %s." % (username)
        print e.message
        return False


def make_admin(user):
    u = User.objects.get(username=user)
    u.is_superuser = True
    u.is_staff = True
    u.save()


if __name__ == "__main__":
    main()
