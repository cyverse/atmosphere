#!/usr/bin/env python

from atmosphere import settings
from service.accounts.openstack import AccountDriver
from django.contrib.auth.models import User
from keystoneclient.exceptions import NotFound

def main():
    """
    Generate openstack users then add them to the DB
    """
    driver = AccountDriver()

    success = 0
    core_services = ['esteve', 'edwins', 'jmatt', 'cjlarose','mlent']
    for username in core_services:
        try:
            password = driver.hashpass(username)
            user = driver.get_user(username)
            if not user:
                (username, password) = driver.create_user(username, True, True)
                print 'New OStack User - %s Pass - %s' % (username,password)
            else:
                print 'Found OStack User - %s Pass - %s' % (username,password)
            #ASSERT: User exists on openstack, create an identity for them.
            ident = driver.create_openstack_identity(username, password, tenant_name=username)
            success += 1
            print 'New OStack Identity - %s:%s' % (ident.id, ident)
        except Exception as e:
            print "Problem adding username: %s" % username
            print e
            raise

    print "Total users created:%s/%s" % (success,len(core_services))

if __name__ == "__main__":
    main()
