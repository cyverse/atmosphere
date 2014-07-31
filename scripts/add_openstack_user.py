#!/usr/bin/env python
import argparse

from keystoneclient.exceptions import NotFound

#try:
#    from authentication.protocol.oauth import is_atmo_user
#except ImportError:
from authentication.protocol.ldap import is_atmo_user

from core.email import send_new_provider_email
from core.models import Provider

from service.accounts.openstack import AccountDriver


def main():
    """
    Add a user to openstack.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('users', type=str, nargs='+')
    args = parser.parse_args()
    openstack_prov = Provider.objects.get(location='iPlant Workshop Cloud - Tucson')
    driver = AccountDriver(openstack_prov)
    success = 0
    for username in args.users:
        print "Adding username... %s" % username
        try:
            if not is_atmo_user(username):
                print "User is not in the atmo-user group.\n"\
                    + "User does not exist in Atmosphere."
                raise Exception("User does not exist in Atmosphere.")
            user = driver.get_user(username)
            if not user:
                identity = driver.create_account(username)
                credentials = identity.credential_set.all()
                print 'New OStack User - Credentials: %s ' % (credentials)
                send_new_provider_email(username, "Openstack")
            else:
                password = driver.hashpass(username)
                identity = driver.create_identity(user.name,
                                               password,
                                               project_name=username)
                credentials = identity.credential_set.all()
                print 'Found OStack User - Credentials: %s' % (credentials)
            #ASSERT: User exists on openstack, create an identity for them.
            success += 1
            print 'New OStack Identity - %s:%s' % (identity.id, identity)
        except Exception as e:
            print "Problem adding username: %s" % username
            print e
            raise

    print "Total users created:%s/%s" % (success, len(args.users))

if __name__ == "__main__":
    main()
