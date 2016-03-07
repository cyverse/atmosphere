#!/usr/bin/env python
import argparse
import libcloud.security

import django; django.setup()

from core.models import AtmosphereUser as User
from core.models import Provider, Identity

from service.accounts.openstack_manager import AccountDriver as OSAccountDriver

from iplantauth.protocol.ldap import get_members
from threepio import logger

libcloud.security.VERIFY_SSL_CERT = False
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
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
        raise Exception("Required argument 'provider' is missing. Please provide the DB ID of the provider to continue.")
    print "Using Provider: %s" % provider
    type_name = provider.type.name.lower()
    if type_name == 'openstack':
        acct_driver = OSAccountDriver(provider)
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
            if not id_exists:
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
