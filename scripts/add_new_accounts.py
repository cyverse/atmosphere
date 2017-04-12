#!/usr/bin/env python

# DEPRECATION WARNING -- Will be removed in favor of periodic task (To facilitate auto-generation of `atmo-user` accounts)
# and the use of the /v2/accounts API.
# FIXME: Add 'account_user, group_name, is_leader' args to this script
import argparse
import libcloud.security

import django
django.setup()

from core.models import AtmosphereUser as User
from core.models import Provider, Identity
from core.query import contains_credential
from core.plugins import ValidationPluginManager, ExpirationPluginManager, AccountCreation

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
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated list with no spaces)")
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
    try:
        acct_driver = get_account_driver(provider, raise_exception=True)
    except:
        account_provider = provider.accountprovider_set.first()
        print "Could not create the account Driver for this Provider."\
              " Check the configuration of this identity:%s" % account_provider
        raise
    if not args.users:
        if not args.rebuild:
            print "Retrieving all 'atmo-user' members in LDAP."
            users = get_members('atmo-user')
        else:
            print "Rebuilding all existing users."
            users = get_usernames(provider)
    else:
        users = args.users.split(",")
    return run_create_accounts(acct_driver, provider, users,
                           args.rebuild, args.admin)


def run_create_accounts(acct_driver, provider, users, rebuild=False, admin=False):
    added = 0
    for user in users:
        new_identities = AccountCreation.create_accounts(provider, user, force=rebuild)
        if new_identities:
            print "%s added." % (user)
            added += len(new_identities)
    print "Total users added:%s" % (added)


def make_admin(user):
    u = User.objects.get(username=user)
    u.is_superuser = True
    u.is_staff = True
    u.save()


if __name__ == "__main__":
    main()
