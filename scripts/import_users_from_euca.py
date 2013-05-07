#!/usr/bin/env python
import time, requests

from django.contrib.auth.models import User

from threepio import logger

from atmosphere import settings

from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver


def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in eucalyptus (Never use in PROD)
    """
    euca_driver = EucaAccountDriver()
    os_driver = OSAccountDriver()
    found = 0
    create = 0
    all_users = euca_driver.list_users()
    for user_dict in all_users.values():
        #Here we don't call create_account to reduce
        ## of calls to euca_driver.get_user
        euca_driver.create_identity(user_dict)
        #os_driver.create_account(user, admin_role=False)
    print "Total users added:%s" % len(all_users)


if __name__ == "__main__":
    main()
