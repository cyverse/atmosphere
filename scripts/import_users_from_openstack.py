#!/usr/bin/env python
import time


from threepio import logger

from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver
from service.accounts.openstack import AccountDriver as OSAccountDriver
from core.models import AtmosphereUser as User
from core.models import Provider

def main():
    """
    TODO: Add argparse, --delete : Deletes existing users in openstack (Never use in PROD)
    """
    euca = Provider.objects.get(location='EUCALYPTUS')
    openstack = Provider.objects.get(location='OPENSTACK')
    euca_driver = EucaAccountDriver(euca)
    os_driver = OSAccountDriver(openstack)
    found = 0
    create = 0
    usernames = os_driver.list_usergroup_names()
    for user in usernames:
        # Add the Euca Account
        #euca_driver.create_account(user)
        # Add the Openstack Account
        os_driver.create_account(user)
    print "Total users added to atmosphere:%s" % len(usernames)

def fix_openstack_network(os_driver):
    """
    DEPRECATED -- Should only be used when tenant networks are permanent..
    Assumes the password can be derived by accountdriver
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

if __name__ == "__main__":
    main()
