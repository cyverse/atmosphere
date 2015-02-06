#!/usr/bin/env python
import argparse
import requests
import time

import libcloud.security

from threepio import logger
from django.db.models import Q

from authentication.protocol.ldap import is_atmo_user, get_members

from core.models import AtmosphereUser as User
from core.models import Provider, Allocation, IdentityMembership

from service.driver import get_account_driver

import django
django.setup()


libcloud.security.VERIFY_SSL_CERT = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocation-list", action="store_true",
                        help="List of allocation names and IDs")
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print, but don't do anything else")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    parser.add_argument("--allocation-id",
                        help="Atmosphere Allocation ID to assign (Optional, instead of default)")
    args = parser.parse_args()
    users = None
    quota = None
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    elif args.allocation_list:
        print "ID\tSpecs"
        for alloc in Allocation.objects.all().order_by('id'):
            print "%s\t%s" % (alloc.id, alloc)
        return

    #Optional args
    if args.dry_run:
        print "Test Run Enabled"
    #Optional args
    if args.allocation_id:
        def_allocation = Allocation.objects.get(id=args.allocation_id)
    else:
        def_allocation = Allocation.default_allocation()

    print "Looking for users with non-default Allocation:%s" % def_allocation
    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return
    members = IdentityMembership.objects.filter(~Q(allocation__id=def_allocation.id),
                                                Q(identity__provider__id=args.provider_id),
                                                identity__created_by__is_staff=False)
    print "Identities with non-default Allocation:%s" % len(members)
    for ident_member in members:
        user = ident_member.member.name
        old_alloc = ident_member.allocation
        ident_member.allocation = def_allocation
        if not args.dry_run:
            ident_member.save()
        print "Updated Allocation for %s (OLD:%s)" % (user, old_alloc)



if __name__ == "__main__":
    main()
