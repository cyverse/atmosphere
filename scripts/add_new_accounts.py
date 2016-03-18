#!/usr/bin/env python
import argparse
import libcloud.security

import django; django.setup()

from core.models import AtmosphereUser as User
from core.models import Provider, Identity

from service.driver import get_account_driver
from threepio import logger

libcloud.security.VERIFY_SSL_CERT = False


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
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users."
                        " DEPRECATION WARNING -- THIS WILL BE REMOVED SOON!")
    parser.add_argument("--provider-list",
                        action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild all accounts that are in the provider")
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
    if args.provider_id and not args.provider:
        print "WARNING: --provider-id has been *DEPRECATED*! Use --provider instead!"
        args.provider = args.provider_id
    if args.provider:
        provider = Provider.objects.get(id=args.provider)
    else:
        raise Exception("Missing required argument: --provider <id>. use --provider-list to get a list of provider ID+names")
    print "Using Provider: %s" % provider
    type_name = provider.type.name.lower()
    acct_driver = get_account_driver(provider)
    if not acct_driver:
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
    return create_accounts(acct_driver, provider, users,
                           args.rebuild, args.admin)


def create_accounts(acct_driver, provider, users, rebuild=False, admin=False):
    added = 0
    for user in users:
        # Then add the Openstack Identity
        try:
            id_exists = Identity.objects.filter(
                created_by__username__iexact=user,
                provider=provider)
            if id_exists and not rebuild:
                print "%s Exists -- Skipping because rebuild flag is disabled" % user
                continue
            acct_driver.create_account(user, role_name='user', max_quota=admin)
            added += 1
            if admin:
                make_admin(user)
                print "%s added as admin." % (user)
            else:
                print "%s added." % (user)
        except Exception as e:
            logger.exception("Problem creating account")
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
