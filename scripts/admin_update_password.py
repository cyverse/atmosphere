#!/usr/bin/env python
import argparse
from hashlib import sha1

import django
django.setup()

from core.models import Provider, Identity
from service.accounts.openstack_manager import AccountDriver as OSAccountDriver


def get_identities(provider, user_list=[]):
    """
    """
    query = Identity.objects.filter(provider=provider)
    if user_list:
        query = query.filter(created_by__username__in=user_list)
    query = query.order_by('created_by__username')
    return query


def get_old_password(accounts, username):
    """
    """
    old_password = accounts.old_hashpass(username)
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
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Do not actually update any passwords")
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
    if args.dry_run:
        print "DRY RUN -- No passwords will be updated!"

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
    return update_password_for(provider, identities, dry_run=args.dry_run, rebuild=args.rebuild)


def skip_change_password(accounts, username, password, new_password, dry_run=False, rebuild=False):
    old_password = get_old_password(accounts, username)
    if dry_run:
        return False
    if old_password != password:
        # Saved password does *NOT* match old..
        if password != new_password:
            print "Skipping user %s - Password (%s) does *NOT* match either "\
                  "hash method (%s, %s)." \
                  % (username, password, old_password, new_password)
            return True
        # ASSERT: Saved Password is 'the new one'
        if not rebuild:
            print "Skipping user %s - Password has been updated previously. "\
                  "If you believe this is wrong, add `--rebuild`" % (username,)
            return True
    return False


def update_password_for(prov, identities, dry_run=False, rebuild=False):
        count = 0
        accounts = OSAccountDriver(prov)
        for ident in identities:
            creds = accounts.parse_identity(ident)
            username = creds['username']
            password = creds['password']  # Represents the *SAVED* password.
            new_password = accounts.hashpass(
                username, strategy='salt_hashpass')
            if skip_change_password(
                    accounts, username, password, new_password,
                    dry_run=dry_run, rebuild=rebuild):
                print "Skipping user %s" % (username,)
                continue
            # ASSERT: Saved Password is 'old'
            print "Changing password: %s (OLD:%s -> NEW:%s)" \
                % (username, password, new_password),
            if dry_run:
                print "OK"
                count += 1
                continue
            kwargs = {}
            if rebuild:
                old_password = get_old_password(accounts, username)
                kwargs.update({'old_password': old_password})
            success = accounts.change_password(
                ident, new_password, **kwargs)
            if success:
                print "OK"
                count += 1
            else:
                print "FAILED"
        print 'Changed passwords for %s accounts on %s' % (count, prov)

if __name__ == "__main__":
    main()
