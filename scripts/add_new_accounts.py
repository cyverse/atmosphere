#!/usr/bin/env python

# DEPRECATION WARNING -- Will be removed in favor of periodic task (To facilitate auto-generation of `atmo-user` accounts)
# and the use of the /v2/accounts API.
# FIXME: Add 'account_user, group_name, is_leader' args to this script
import argparse
import libcloud.security

import django

django.setup()

import core.models
from core.models import AtmosphereUser as User
from core.models import Provider, Identity
from core.query import contains_credential
from core.plugins import ValidationPluginManager, ExpirationPluginManager, AccountCreationPluginManager

from django_cyverse_auth.protocol.ldap import get_members
from service.driver import get_account_driver
from threepio import logger

libcloud.security.VERIFY_SSL_CERT = False


def get_usernames(provider):
    """
    """
    return Identity.objects.filter(provider=provider).values_list('created_by__username', flat=True)

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
    parser.add_argument("--group",
                        help="LDAP group of usernames to import.")
    parser.add_argument("--users",
                        help="usernames to add to Atmosphere. (comma separated list with no spaces)")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    args = parser.parse_args()

    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return

    usernames = []
    if args.provider_id and not args.provider:
        print "WARNING: --provider-id has been *DEPRECATED*! Use --provider instead!"
        args.provider = args.provider_id
    if args.provider:
        provider = Provider.objects.get(id=args.provider)
    else:
        raise Exception("Missing required argument: --provider <id>. use --provider-list to get a list of provider ID+names")
    print "Using Provider: %s" % provider
    try:
        acct_driver = get_account_driver(provider, raise_exception=True)
    except:
        account_provider = provider.accountprovider_set.first()
        print "Could not create the account Driver for this Provider."\
              " Check the configuration of this identity:%s" % account_provider
        raise
    if args.group:
        print "Retrieving all '%s' members in LDAP." % args.group
        usernames = get_members(args.group)
    elif args.users:
        usernames = args.users.split(",")
    else: # if not args.users
        if not args.rebuild:
            print "Retrieving all 'atmo-user' members in LDAP."
            usernames = get_members('atmo-user')
        else:
            print "Rebuilding all existing users."
            usernames = get_usernames(provider)
    return run_create_accounts(acct_driver, provider, usernames,
                               args.rebuild, args.admin)


def run_create_accounts(acct_driver, provider, usernames, rebuild=False, admin=False):
    user_total = 0
    identity_total = 0
    for username in sorted(usernames):
        new_identities = AccountCreationPluginManager.create_accounts(provider, username, force=rebuild)
        if new_identities:
            count = len(new_identities)
            print "%s new identities identity_total for %s." % (count, username)
            identity_total += count
            user_total += 1
        if admin:
            make_admin(username)
    print "%s Total identities identity_total for %s users" % (identity_total, user_total)


def make_admin(username):
    u = User.objects.get(username=username)
    u.is_superuser = True
    u.is_staff = True
    u.save()


if __name__ == "__main__":
    main()
