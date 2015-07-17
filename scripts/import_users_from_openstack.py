#!/usr/bin/env python
import time
import requests


from threepio import logger

from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver
from core.models import AtmosphereUser as User
from core.models import Provider, Quota
import django
django.setup()


def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in openstack (Never use in PROD)
    """
    openstack = Provider.objects.filter(
        type__name__iexact="openstack").order_by("id")
    if not openstack:
        raise Provider.DoesNotExist("No OpenStack Provider Found")
    openstack = openstack[0]
    os_driver = OSAccountDriver(openstack)
    found = 0
    create = 0
    usernames = os_driver.list_usergroup_names()
    quota_dict = {
        'cpu': 10,
        'memory': 20,
        'storage': 10,
        'storage_count': 10
    }
    higher_quota = Quota.objects.get_or_create(**quota_dict)[0]
    for user in usernames:
        # Openstack account exists, but we need the identity.
        ident = os_driver.create_account(user)
        if is_staff(ident):
            im = ident.identity_membership.all()[0]
            # Disable time allocation
            im.allocation = None
        # Raise everybody's quota
        im.quota = higher_quota
        im.save()
    print "Total users added to atmosphere:%s" % len(usernames)


def is_staff(core_identity):
    # Query Groupy
    staff_users = []
    if not staff_users:
        staff_users = members_query_groupy("staff")
    if core_identity.created_by.username in staff_users:
        return True
    return False


def members_query_groupy(groupname):
    r = requests.get(
        'http://gables.iplantcollaborative.org/groups/%s/members'
        % groupname)
    json_obj = r.json()
    usernames = []
    for user in json_obj['data']:
        usernames.append(user['name'].replace('esteve', 'sgregory'))
    return usernames


def fix_openstack_network(os_driver):
    """
    DEPRECATED -- Should only be used when tenant networks are permanent..
    Assumes the password can be derived by accountdriver
    """
    usergroups = [usergroup for usergroup in os_driver.list_usergroups()]
    users_with_networks = os_driver.network_manager.list_tenant_network()
    users_without_networks = []
    for (user, group) in usergroups:
        if user.name not in users_with_networks:
            # This user needs to have a tenant network created
            password = os_driver.hashpass(user.name)
            os_driver.network_manager.create_tenant_network(
                user.name,
                password,
                group.name)
            logger.info("Tenant network built for %s" % user.name)

if __name__ == "__main__":
    main()
