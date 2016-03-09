#!/usr/bin/env python
import argparse
from hashlib import sha1

from core.models import Provider, Identity
from service.accounts.openstack_manager import AccountDriver as OSAccountDriver

import django
from django.db.models import ObjectDoesNotExist
from keystoneclient.apiclient.exceptions import Unauthorized
django.setup()


def get_identities(provider, user_list=[]):
    """
    """
    query = Identity.objects.filter(provider=provider)
    if user_list:
        query = query.filter(created_by__username__in=user_list)
    return query


def old_password_match(username, password):
    """
    True if the password passed matches the 'old method'
    """
    old_password = sha1(username).hexdigest()
    return old_password == password


def main():
    """
    Using the old method of hashing a password, find all accounts that
    still use the 'old method' and replace the password by 'changing_password' for the user.

    It is essential that all users use the same password-generation methods
    to avoid collisions between deployments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--rebuild",
                        action="store_true",
                        help="Force a 'rebuild' of the script (Will attempt to change password anyway)")
    parser.add_argument("--provider-list",
                        action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--users",
                        help="LDAP usernames to import. (comma separated)")
    args = parser.parse_args()

    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return

    if args.provider:
        provider = Provider.objects.get(id=args.provider)
    else:
        raise Exception("Missing required argument: --provider <id>. use --provider-list to get a list of provider ID+names")

    identities = None
    if not args.users:
        identities = get_identities(provider)
    else:
        identities = get_identities(provider, args.users.split(","))
    print "Update password on %s for %s accounts" % (provider.location, len(identities))
    return update_password_for(provider, identities, rebuild=args.rebuild)


def update_password_for(prov, identities, rebuild=False):
        count = 0
        os_accounts = OSAccountDriver(prov)
        for ident in identities:
            creds = os_accounts.parse_identity(ident)
            username = creds['username']
            password = creds['password']  # Represents the *SAVED* password.
            old_password = sha1(username).hexdigest()
            new_password = os_accounts.hashpass(username)
            if not old_password_match(username, password):
                # Saved password does *NOT* match old..
                if password != new_password:
                    print "Skipping user %s - Password (%s) does *NOT* match either hash method (%s, %s)." % (username, password, old_password, new_password)
                    continue
                # ASSERT: Saved Password is 'the new one'
                if not rebuild:
                    print "Skipping user %s - Password has been updated previously. If you believe this is in err, add `--rebuild`" % (username,)
                    continue
            # ASSERT: Saved Password is 'old'
            if rebuild:
                password = old_password
            print "Changing password: %s (OLD:%s -> NEW:%s)" % (username, password, new_password)
            try:
                clients = os_accounts.get_openstack_clients(username, password, creds['tenant_name'])
                keystone = clients['keystone']
            except Unauthorized:
                print "Skipping user %s - The password may have already been changed -- %s password: %s no longer valid."\
                    % (username, "old" if rebuild else "saved", password)
                continue

            try:
                keystone.users.update_password(password, new_password)
            except Unauthorized:
                print "Keystone validated but the password could not be updated for %s." \
                    % (creds['username'],)
                continue

            try:
                password_cred = ident.credential_set.get(key='secret')
                password_cred.value = new_password
                password_cred.save()
                print "Updated password for user %s"\
                    % (creds['username'],)
                count += 1
            except ObjectDoesNotExist:
                raise Exception(
                    "The 'key' for a secret has changed! "
                    "Ask a programmer for help!")
        print 'Changed passwords for %s accounts on %s' % (count, prov)

if __name__ == "__main__":
    main()
