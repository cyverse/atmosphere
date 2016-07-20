#!/usr/bin/env python

from atmosphere import settings
from core.models import Provider, Identity
from service.accounts.openstack_manager import AccountDriver as OSAccountDriver
from rtwo.exceptions import KeystoneUnauthorized
import django
django.setup()


def main():
    """
    Using the keyname and public_key defined in settings
    Ensure that the keypair has been distributed to every identity on the
    provider.
    It is essential that all users carry the same keypair to allow Deployment
    access
    """
    keyname = settings.ATMOSPHERE_KEYPAIR_NAME
    with open(settings.ATMOSPHERE_KEYPAIR_FILE, 'r') as pub_key_file:
        public_key = pub_key_file.read()
    print "Adding keypair: %s Contents: %s" % (keyname, public_key)
    os_providers = Provider.objects.filter(type__name="OpenStack")
    for prov in os_providers:
        count = 0
        identities = Identity.objects.filter(provider=prov)
        os_accounts = OSAccountDriver(prov)
        for ident in identities:
            creds = os_accounts.parse_identity(ident)
            try:
                (keypair, created) = os_accounts.get_or_create_keypair(
                    creds['username'], creds['password'], creds['tenant_name'],
                    keyname, public_key)
            except KeystoneUnauthorized as exc:
                print "Could not create keypair for %s. Error message: %s"\
                    % (creds['username'], exc.message)
            if created:
                print "Created keypair %s for user %s"\
                    % (keypair, creds['username'])
                count += 1
        print 'Keypairs added for %s accounts on %s' % (count, prov)

if __name__ == "__main__":
    main()
