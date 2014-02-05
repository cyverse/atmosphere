#!/usr/bin/env python
import time
import requests


from threepio import logger

from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver
from core.models import AtmosphereUser as User
from core.models import Provider, Quota, Allocation, Identity, IdentityMembership
from authentication.protocol.ldap import get_staff_users

def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in openstack (Never use in PROD)
    """
    openstack = Provider.objects.get(location='OpenStack-Tucson (BETA)')
    os_driver = OSAccountDriver(openstack)
    found = 0
    create = 0
    quota_dict = {
        'cpu':16,
        'memory': 128,
        'storage': 10,
        'storage_count': 10
    }
    higher_quota = Quota.objects.get_or_create(**quota_dict)[0]

    usernames = os_driver.list_usergroup_names()
    staff = get_staff_users()

    staff_users = sorted(list(set(staff) & set(usernames)))
    non_staff = sorted(list(set(usernames) - set(staff)))
    non_staff = non_staff[2069:]
    for user in non_staff:
        #Raise everybody's quota
        #try:
        im_list = IdentityMembership.objects.filter(identity__created_by__username=user, identity__provider=openstack)
        if not im_list:
            print "Missing user:%s" % user
            continue
        im = im_list[0]
        if im.quota.cpu == quota_dict["cpu"]:
            continue
        print "Existing Quota CPU:%s should be %s" % (im.quota.cpu, quota_dict["cpu"])
        im.quota = higher_quota
        im.allocation = Allocation.default_allocation()
        im.save()
        print 'Found non-staff user:%s -- Update quota and add allocation' % user
    for user in staff_users:
        # Openstack account exists, but we need the identity.
        im = IdentityMembership.objects.filter(identity__created_by__username=user, identity__provider=openstack)
        if not im:
            print "Missing user:%s" % user
            continue
        im = im[0]
        if im.quota.cpu == quota_dict["cpu"]:
            continue
        #Disable time allocation
        im.allocation = None
        im.quota = higher_quota
        im.save()
        print 'Found staff user:%s -- Update quota and no allocation' % user
    print "Total users added to atmosphere:%s" % len(usernames)




if __name__ == "__main__":
    main()
