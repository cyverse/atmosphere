#!/usr/bin/env python
import argparse
import requests
import time
import libcloud.security

import django
django.setup()

from core.models import AtmosphereUser as User
from core.models import Provider, Identity

from service.accounts.openstack_manager import AccountDriver as OSAccountDriver
from threepio import logger

libcloud.security.VERIFY_SSL_CERT = False
# TODO: Remove this and use 'get_members' in iplantauth/protocols/ldap.py
#      when it exists (A-N)


def get_usernames(provider):
    """
    """
    return Identity.objects.filter(provider=provider).values_list('created_by__username', flat=True)

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
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild all accounts that are in the provider")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    args = parser.parse_args()
    users = None
    added = 0
    if args.provider:
        provider = Provider.objects.get(id=args.provider)
    else:
        provider = Provider.objects.get(location='JetStream - Indiana')
    print "Using Provider: %s" % provider
    type_name = provider.type.name.lower()
    if type_name == 'openstack':
        acct_driver = OSAccountDriver(provider)
    elif type_name == 'eucalyptus':
        acct_driver = EucaAccountDriver(provider)
    else:
        raise Exception("Could not find an account driver for Provider with"
                        " type:%s" % type_name)
    if not args.users:
        if not args.rebuild:
            print "Retrieving all 'atmo-user' members in LDAP."
            users = get_members('atmo-user')
        else:
            print "Rebuilding all existing users."
            users = get_usernames(provider)
    else:
        users = args.users.split(",")
    for user in users:
        # Then add the Openstack Identity
        try:
            id_exists = Identity.objects.filter(
                created_by__username__iexact=user,
                provider=provider)
            if id_exists and not args.rebuild:
                print "%s Exists -- Skipping because rebuild flag is disabled" % user
                continue
            acct_driver.create_account(user, role_name='user', max_quota=args.admin)
            added += 1
            if args.admin:
                make_admin(user)
                print "%s added as admin." % (user)
            else:
                print "%s added." % (user)
        except Exception as e:
            print "Problem adding %s." % (user)
            logger.exception(e)
            print e.message
    print "Total users added:%s" % (added)


def make_admin(user):
    u = User.objects.get(username=user)
    u.is_superuser = True
    u.is_staff = True
    u.save()


if __name__ == "__main__":
    main()
