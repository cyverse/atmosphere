#!/usr/bin/env python

# DEPRECATION WARNING -- Will be removed in favor of periodic task (To facilitate auto-generation of `atmo-user` accounts)
# and the use of the /v2/accounts API.
import argparse
import libcloud.security

import django

django.setup()

import core.models
from core.models import AtmosphereUser as User
from core.models import Provider, Identity

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
                        help="LDAP usernames to import. (comma separated list with no spaces)")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    args = parser.parse_args()

    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return

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
    return create_accounts(acct_driver, provider, usernames, args.rebuild, args.admin)


def create_accounts(acct_driver, provider, usernames, rebuild=False, admin=False):
    added = 0
    for username in usernames:
        # Then add the Openstack Identity
        try:
            id_exists = Identity.objects.filter(
                created_by__username__iexact=username,
                provider=provider)
            if id_exists:
                if not rebuild:
                    continue
                print "%s Exists -- Attempting an account rebuild" % username
            user, group = core.models.Group.create_usergroup(username=username, group_name=username)
            logger.debug('user: %s, group: %s', user, group)

            new_identity = acct_driver.create_account(username, max_quota=admin)
            # After identity is created, be sure to select one of the
            # `public_routers` in provider to be given
            # to the identity as a `router_name`
            selected_router = provider.select_router()
            Identity.update_credential(
                new_identity, 'router_name', selected_router,
                replace=True)
            added += 1
            if admin:
                make_admin(username)
                print "%s added as admin." % (username)
            else:
                print "%s added." % (username)
        except Exception as e:
            logger.exception("Problem creating account")
            print "Problem adding %s." % (username)
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
