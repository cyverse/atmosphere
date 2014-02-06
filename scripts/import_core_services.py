#!/usr/bin/env python
import time
import requests

import libcloud.security

from threepio import logger

from core.models import AtmosphereUser as User
from core.models import Provider

from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver

libcloud.security.VERIFY_SSL_CERT = False
libcloud.security.VERIFY_SSL_CERT_STRICT = False


def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in openstack
          (Never use in PROD)
    """
    euca_driver = EucaAccountDriver(
        Provider.objects.get(location='EUCALYPTUS'))
    os_driver = OSAccountDriver(Provider.objects.get(location='iPlant Cloud - Tucson'))
    found = 0
    create = 0
    core_services = ['estevetest03', ]  # get_core_services()
    for user in core_services:
        euca_driver.create_account(user, max_quota=True)
        # Then add the Openstack Identity
        os_driver.create_account(user, max_quota=True)
        make_admin(user)
    print "Total core-service/admins added:%s" % len(core_services)


def get_core_services():
    """
    Calls groupy to return list of core-services users, adds users to list
    """
    core_services = members_query_groupy('core-services')
    atmo_users = members_query_groupy('atmo-user')
    users = [user for user in core_services if user in atmo_users]
    return users


def members_query_groupy(groupname):
    r = requests.get(
        'http://gables.iplantcollaborative.org/groups/%s/members'
        % groupname)
    json_obj = r.json()
    usernames = []
    for user in json_obj['data']:
        usernames.append(user['name'].replace('esteve', 'sgregory'))
    return usernames


def make_admin(user):
    u = User.objects.get(username=user)
    u.is_superuser = True
    u.is_staff = True
    u.save()


if __name__ == "__main__":
    main()
