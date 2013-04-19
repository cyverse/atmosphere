#!/usr/bin/env python
import time

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
    usernames = os_driver.list_usergroup_names()
    for user in usernames:
        # Add the Euca Account
        euca_driver.create_account(user)
        # Add the Openstack Account
        os_driver.create_account(user, admin_role=False)
    print "Total users added to atmosphere:%s" % len(usernames)

def fix_openstack_network(os_driver):
    """
    DEPRECATED -- Should only be used when tenant networks are permanent 
    """
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

def create_euca_account(euca_driver, user_dict):
    id = euca_driver.create_identity(user_dict)
    return id

def create_os_account(os_driver, username, admin_role=False):
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
                                                tenant_name=username)
    return ident


if __name__ == "__main__":
    main()
