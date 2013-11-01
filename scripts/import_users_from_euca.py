#!/usr/bin/env python
import time, requests

from core.models import AtmosphereUser as User
from threepio import logger

from atmosphere import settings
from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from core.models import Provider
from django.contrib.auth.models import User

def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in eucalyptus (Never use in PROD)
    """
    euca = Provider.objects.get(location='EUCALYPTUS')
    euca_driver = EucaAccountDriver(euca)
    all_users = euca_driver.list_users()
    total = 0
    for user_dict in all_users.values():
        if not User.objects.filter(username=user_dict['username']):
            euca_driver.create_account(user_dict)
            total += 1
            print "Added user: %s" % user_dict['username']
    print "Total users added:%s" % total

if __name__ == "__main__":
    main()
