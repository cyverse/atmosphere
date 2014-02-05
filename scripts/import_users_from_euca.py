#!/usr/bin/env python
import time, requests

from threepio import logger

from atmosphere import settings
from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver
from core.models import Provider, Identity
from core.models import AtmosphereUser as User

include_openstack = True

def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in eucalyptus (Never use in PROD)
    """
    euca = Provider.objects.get(location='EUCALYPTUS')
    euca_driver = EucaAccountDriver(euca)
    openstack = Provider.objects.get(location='iPlant Cloud - Tucson')
    os_driver = OSAccountDriver(openstack)
    all_users = euca_driver.list_users()
    #Sort by users
    all_values = sorted(all_users.values(), key=lambda user: user['username'])
    total = 0
    for user_dict in all_values:
        id_exists = Identity.objects.filter(
                created_by__username=user_dict['username'],
                provider=euca)
        if not id_exists:
            euca_driver.create_account(user_dict)
            total += 1
            print "Added to Eucalyptus: %s" % user_dict['username']
    print "Total users added:%s" % total
    if include_openstack:
        print "Adding all eucalyptus users to openstack"
        total = 0
        for user_dict in all_values:
            id_exists = Identity.objects.filter(
                    created_by__username=user_dict['username'],
                                    provider=openstack)
            if not id_exists:
                os_driver.create_account(user_dict['username'])
                total += 1
                print "Added to Openstack: %s" % user_dict['username']
        print "Total users added to openstack:%s" % total

if __name__ == "__main__":
    main()
