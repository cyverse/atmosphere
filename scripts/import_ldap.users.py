#!/usr/bin/env python
import argparse
import requests
import time

import libcloud.security

from threepio import logger

from authentication.protocol.ldap import is_atmo_user

from core.models import AtmosphereUser as User
from core.models import Provider

from service.accounts.openstack import AccountDriver as OSAccountDriver


libcloud.security.VERIFY_SSL_CERT = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("users",
                        help="LDAP usernames to import. (comma separated)")
    parser.add_argument("--admin", action="store_true",
                        help="Users addded as admin and staff users.")
    args = parser.parse_args()
    users = None
    added = 0
    if args.provider:
        os_driver = OSAccountDriver(Provider.objects.get(id=args.provider))
    else:
        os_driver = OSAccountDriver(
            Provider.objects.get(location='iPlant Workshop Cloud - Tucson'))
    users = args.users.split(",")
    for user in users:
        # Then add the Openstack Identity
        try:
            if is_atmo_user(user):
                os_driver.create_account(user, max_quota=args.admin)
                added += 1
            else:
                print "%s is not in the ldap atmosphere group (atmo-user)." % (user)
                continue
            if args.admin:
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
