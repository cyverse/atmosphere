#!/usr/bin/env python
import time
import requests


from threepio import logger

from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver
from core.models import AtmosphereUser as User
from core.models import Provider, Quota, Allocation

def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in openstack (Never use in PROD)
    """
    openstack = Provider.objects.get(location='OpenStack-Tucson (BETA)')
    os_driver = OSAccountDriver(openstack)
    found = 0
    create = 0
    quota_dict = {
        'cpu':10,
        'memory': 20,
        'storage': 10,
        'storage_count': 10
    }
    higher_quota = Quota.objects.get_or_create(**quota_dict)[0]

    usernames = os_driver.list_usergroup_names()
    staff = members_query_groupy("staff")

    staff_users = list(set(staff) & set(usernames))
    non_staff = list(set(usernames) - set(staff))

    for user in staff_users:
        # Openstack account exists, but we need the identity.
        ident = os_driver.create_account(user)
        print 'Found staff user:%s -- Remove allocation and Update quota' % user
        im = ident.identitymembership_set.all()[0]
        #Disable time allocation
        im.allocation = None
        im.quota = higher_quota
        im.save()
    for user in non_staff:
        #Raise everybody's quota
        ident = os_driver.create_account(user)
        im = ident.identitymembership_set.all()[0]
        im.quota = higher_quota
        im.allocation = Allocation.default_allocation()
        im.save()
        print 'Found non-staff user:%s -- Update quota' % user
    print "Total users added to atmosphere:%s" % len(usernames)


def members_query_groupy(groupname):
    r = requests.get(
        'http://gables.iplantcollaborative.org/groups/%s/members'
        % groupname)
    json_obj = r.json()
    usernames = []
    for user in json_obj['data']:
	    usernames.append(user['name'].replace('esteve','sgregory'))
    return usernames


if __name__ == "__main__":
    main()
