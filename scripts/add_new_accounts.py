#!/usr/bin/env python
import argparse
import requests
import time
import libcloud.security

import django
django.setup()

from core.models import AtmosphereUser as User
from core.models import Provider, Identity

from service.driver import get_account_driver
from threepio import logger

libcloud.security.VERIFY_SSL_CERT = False
# TODO: Remove this and use 'get_members' in iplantauth/protocols/ldap.py
#      when it exists (A-N)


def get_members(groupname):
    """
    """
    from atmosphere.settings import secrets
    import ldap as ldap_driver
    try:
        ldap_server = secrets.LDAP_SERVER
        ldap_group_dn = secrets.LDAP_SERVER_DN.replace(
            "ou=people", "ou=Groups")
        ldap_conn = ldap_driver.initialize(ldap_server)
        group_users = ldap_conn.search_s(ldap_group_dn,
                                         ldap_driver.SCOPE_SUBTREE,
                                         '(cn=%s)' % groupname)
        all_users = group_users[0][1]['memberUid']
        return sorted(all_users)
    except Exception as e:
        print "Error finding members for group %s" % groupname
        print e
        return []

# DEPRECATION WARNING: DO NOT USE THIS SCRIPT!
# There is an updated script here:
# <atmosphere_dir>/scripts/import_users_from_ldap.py


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users."
                        " DEPRECATION WARNING -- THIS WILL BE REMOVED SOON!")
    parser.add_argument("--provider-list",
                        action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    args = parser.parse_args()
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return

    users = None
    added = 0
    if args.provider_id and not args.provider:
        print "WARNING: --provider-id has been *DEPRECATED*! Use --provider instead!"
        args.provider = args.provider_id
    if args.provider:
        provider = Provider.objects.get(id=args.provider)
    else:
        provider = Provider.objects.get(location='iPlant Cloud - Tucson')
    print "Using Provider: %s" % provider
    type_name = provider.type.name.lower()
    if type_name == 'openstack':
        acct_driver = get_account_driver(provider)
    else:
        raise Exception("Could not find an account driver for Provider with"
                        " type:%s" % type_name)
    if not args.users:
        print "Retrieving all 'atmo-user' members in LDAP."
        users = get_members('atmo-user')
    else:
        users = args.users.split(",")
    for user in users:
        # Then add the Openstack Identity
        try:
            id_exists = Identity.objects.filter(
                created_by__username__iexact=user,
                provider=provider)
            if id_exists:
                continue
            acct_driver.create_account(user, max_quota=args.admin)
            added += 1
            if args.admin:
                make_admin(user)
                print "%s added as admin." % (user)
            else:
                print "%s added." % (user)
        except Exception as e:
            logger.exception("Problem creating account")
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
