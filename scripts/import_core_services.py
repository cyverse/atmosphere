#!/usr/bin/env python
import time, requests

from django.contrib.auth.models import User

from novaclient.exceptions import OverLimit

from atmosphere import settings
from atmosphere.logger import logger

from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver


def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in openstack (Never use in PROD)
    """
    euca_driver = EucaAccountDriver()
    os_driver = OSAccountDriver()
    found = 0
    create = 0
    core_services = get_core_services()
    for user in core_services:
        # Get the user from Euca DB
        user_dict = euca_driver.get_user(user)
        # Create a euca account/identity
        create_euca_account(euca_driver, user_dict, max_quota=True)
        # Then add the Openstack Identity
        create_os_account(os_driver, user, admin_role=True, max_quota=True)
        make_admin(user)
    print "Total core-service/admins added:%s" % len(core_services)

def get_core_services():
    """
    Calls groupy to return list of core-services users, adds users to list
    """
    core_services = members_query_groupy('core-services')
    atmo_users = members_query_groupy('atmo-user')
    return [user for user in core_services if user in atmo_users]

def members_query_groupy(groupname):
    r = requests.get(
        'http://gables.iplantcollaborative.org:8080/groups/%s/members'
        % groupname)
    json_obj = r.json()
    usernames = []
    for user in json_obj['data']:
	    usernames.append(user['name'])
    return usernames

def fix_openstack_network(os_driver):
    usergroups = [usergroup for usergroup in os_driver.list_usergroups()]
    users_with_networks = os_driver.network_manager.list_tenant_network()
    users_without_networks = []
    for (user,group) in usergroups:
        if user.name not in users_with_networks:
            # This user needs to have a tenant network created
            password = os_driver.hashpass(user.name)
            os_driver.network_manager.create_tenant_network(user.name, password,
                group.name)
            logger.info("Tenant network built for %s" % user.name)

def add_all_users(euca_driver, os_driver, addOpenstack=False):
    all_users = euca_driver.list_users()
    for user_dict in all_users.values():
        create_euca_account(euca_driver, user_dict)
        if addOpenstack:
            create_os_account(os_driver, user, False)
    print "Total users added:%s" % len(all_users)

def make_admin(user):
    u = User.objects.get(username=user)
    u.is_superuser = True
    u.is_staff = True
    u.save()

def create_euca_account(euca_driver, user_dict, max_quota=False):
    id = euca_driver.create_identity(user_dict, max_quota=max_quota)
    return id

def create_os_account(os_driver, username, admin_role=False, max_quota=False):
    finished = False
    # Special case for admin.. Use the Openstack admin identity..
    if username == 'admin':
        ident = os_driver.create_openstack_identity(
            settings.OPENSTACK_ADMIN_KEY,
            settings.OPENSTACK_ADMIN_SECRET,
            settings.OPENSTACK_ADMIN_TENANT)
        return ident
    #Attempt account creation
    while not finished:
        try:
            password = os_driver.hashpass(username)
            user = os_driver.get_or_create_user(username, password, True, admin_role)
            logger.debug(user)
            tenant = os_driver.get_tenant(username)
            logger.debug(tenant)
            roles = user.list_roles(tenant)
            logger.debug(roles)
            if not roles:
                os_driver.user_manager.add_tenant_member(username,
                                                       username,
                                                       admin_role)
            finished = True
        except OverLimit:
            print 'Requests are rate limited. Pausing for one minute.'
            time.sleep(60)  # Wait one minute
    ident = os_driver.create_openstack_identity(username,
                                                password,
                                                tenant_name=username, max_quota=max_quota)
    return ident


if __name__ == "__main__":
    main()
