#!/usr/bin/env python
import argparse
from hashlib import sha1

from core.models import Provider, Identity
from service.accounts.openstack_manager import AccountDriver as OSAccountDriver

import django
django.setup()


def get_identities(provider, user_list=[]):
    """
    """
    query = Identity.objects.filter(provider=provider)
    if user_list:
        query = query.filter(created_by__username__in=user_list)
    return query


def get_old_password(username):
    """
    """
    old_password = sha1(username).hexdigest()
    return old_password


def main():
    """
    Using the old method of hashing a password,
    find all accounts that still use the 'old method'
    and replace the password by
    calling 'accounts.change_password()' for the user.

    It is essential that all users use the same password-generation methods
    to avoid collisions between deployments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--rebuild",
                        action="store_true",
                        help="Force a 'rebuild' of the script "
                             "(Will attempt to change password anyway)")
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
        raise Exception(
            "Missing required argument: --provider <id>. "
            "use --provider-list to get a list of provider ID+names")

    identities = None
    if not args.users:
        identities = get_identities(provider)
    else:
        identities = get_identities(provider, args.users.split(","))
    print "Update password on %s for %s accounts" \
        % (provider.location, len(identities))
    return update_password_for(provider, identities, rebuild=args.rebuild)


def skip_change_password(username, password, new_password, rebuild=False):
    old_password = get_old_password(username)
    if old_password != password:
        # Saved password does *NOT* match old..
        if password != new_password:
            print "Skipping user %s - Password (%s) does *NOT* match either "\
                  "hash method (%s, %s)." \
                  % (username, password, old_password, new_password)
            continue
        # ASSERT: Saved Password is 'the new one'
        if not rebuild:
            print "Skipping user %s - Password has been updated previously. "\
                  "If you believe this is wrong, add `--rebuild`" % (username,)
            continue


def update_password_for(prov, identities, rebuild=False):
        count = 0
        accounts = OSAccountDriver(prov)
        for ident in identities:
            creds = accounts.parse_identity(ident)
            username = creds['username']
            password = creds['password']  # Represents the *SAVED* password.
            new_password = accounts.hashpass(username)
            if skip_change_password(
                    username, password, new_password, rebuild=rebuild):
                print "Skipping user %s" % (username,)
                continue
            # ASSERT: Saved Password is 'old'
            print "Changing password: %s (OLD:%s -> NEW:%s)" \
                % (username, password, new_password)
            kwargs = {}
            if rebuild:
                old_password = get_old_password(username)
                kwargs.update({'old_password': old_password})
            success = accounts.change_password(
                ident, new_password, **kwargs)
            if success:
                count += 1
        print 'Changed passwords for %s accounts on %s' % (count, prov)

if __name__ == "__main__":
    main()
