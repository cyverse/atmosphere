#!/usr/bin/env python
#NOTE: REMOVE THIS FILE BEFORE PULLING ABYSINNIAN. This is the WRONG one to keep! -Steve
import argparse
import requests
import time

import libcloud.security

from threepio import logger

from authentication.protocol.ldap import is_atmo_user
from core.models import AtmosphereUser as User
from core.models import Provider, Quota


libcloud.security.VERIFY_SSL_CERT = False
from atmosphere.settings import secrets
import ldap as ldap_driver

def get_members(groupname):
    """
    """
    try:
        ldap_server = secrets.LDAP_SERVER
        ldap_group_dn = secrets.LDAP_SERVER_DN.replace(
            "ou=people", "ou=Groups")
        ldap_conn = ldap_driver.initialize(ldap_server)
        group_users = ldap_conn.search_s(ldap_group_dn,
                                        ldap_driver.SCOPE_SUBTREE,
                                        '(cn=%s)' % groupname)
        return group_users[0][1]['memberUid']
    except Exception as e:
        logger.exception(e)
        return []
from service.accounts.openstack import AccountDriver as\
        OSAccountDriver
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    parser.add_argument("--groups",
                        help="LDAP groups to import. (comma separated)")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--quota-id",
                        help="Atmosphere Quota ID to assign (Optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="A 'dry-run' so you know what will happen,"
                             " before it happens")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    args = parser.parse_args()
    make_admins = args.admin
    dry_run = args.dry_run
    users = None
    added = 0
    quota = None
    if dry_run:
        print "Dry run initialized"
    if args.quota_id:
        quota = Quota.objects.get(id=args.quota_id)
    if args.provider_id:
        provider = Provider.objects.get(id=args.provider_id)
        print "Provider Selected:%s" % provider
        acct_driver = OSAccountDriver(provider)
    else:
        provider = Provider.objects.get(location='iPlant Workshop Cloud - Tucson')
        print "No Provider Selected, using default provider: %s" % provider
        acct_driver = OSAccountDriver(provider)

    groups = args.groups.split(",") if args.groups else []
    for groupname in groups:
        group_add = 0
        users = get_members(groupname)
        print "Total users in group %s:%s" % (groupname, len(users))
        for user in users:
            try:
                if is_atmo_user(user):
                    if not dry_run:
                        acct_driver.create_account(user, quota=quota, max_quota=make_admins)
                    group_add += 1
                else:
                    print "%s is not in the ldap atmosphere group (atmo-user)." % (user)
                    continue
                if make_admins:
                    if not dry_run:
                        make_admin(user)
                    print "%s added as admin." % (user)
                else:
                    print "%s added." % (user)
            except Exception as e:
                print "Problem adding %s." % (user)
                print e.message
        print "Added %s users from group %s." % (group_add, groupname)
        added += group_add
    user_list = args.users
    users = user_list.split(",") if user_list else []
    for user in users:
        # Then add the Openstack Identity
        try:
            if is_atmo_user(user):
                if not dry_run:
                    acct_driver.create_account(user, quota=quota, max_quota=make_admins)
                added += 1
            else:
                print "%s is not in the ldap atmosphere group (atmo-user)." % (user)
                continue
            if make_admins:
                if not dry_run:
                    make_admin(user)
                print "%s added as admin." % (user)
            else:
                print "%s added." % (user)
        except Exception as e:
            print "Problem adding %s." % (user)
            print e.message
    print "Total users added:%s" % (added)


def make_admin(user):
    u = User.objects.get(username=user)
    u.is_superuser = True
    u.is_staff = True
    u.save()


if __name__ == "__main__":
    main()
