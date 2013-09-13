#!/usr/bin/env python
import time, requests

from django.contrib.auth.models import User
from threepio import logger

from atmosphere import settings
from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from django.contrib.auth.models import User

def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in eucalyptus (Never use in PROD)
    """
    euca_driver = EucaAccountDriver()
    all_users = euca_driver.list_users()
    total = 0
    for user_dict in all_users.values():
        if not User.objects.filter(username=user_dict['username']):
            euca_driver.create_account(user_dict)
            total += 1
    print "Total users added:%s" % total

if __name__ == "__main__":
    main()
