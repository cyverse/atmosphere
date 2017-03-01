#!/usr/bin/env python

description = """
This script makes an Application (a.k.a. image) available on a specified new
provider by doing the following:

 - Creates models (ProviderMachine, InstanceSource) in Atmosphere database
 - Transfers image data using Glance API (or using iRODS for Atmosphere(0))
 - Populates image metadata
 - (Future coming soon) if Application uses an AMI-style image, ensures the
   kernel (AKI) and ramdisk (ARI) images are also present on destination
   provider, and sets appropriate properties

Gracefully handles the case where destination provider is already partially
populated with image data/metadata (missing information will be added).

If the application owner has no identity on the destination provider, script
will exit with error unless --ignore_missing_owner is set.

If a non-public application has or more members without identities on the
destination provider, script will exit with error unless
--ignore_missing_members is set.
"""

import argparse
import core.models

parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("provider_id", type=int, help="Destination provider ID")
parser.add_argument("application_id", help="Application ID to be migrated")
parser.add_argument("--irods-xfer",
                    action="store_true",
                    help="Transfer image data using iRODS instead of glance download/upload "
                         "(Atmosphere(0)-specific feature)")
parser.add_argument("--ignore-missing-owner",
                    action="store_true",
                    help="Transfer image if application owner has no identity on destination provider (owner will be "
                         "set to Atmosphere admin role")
parser.add_argument("--ignore-missing-members",
                    action="store_true",
                    help="Transfer image if application is private and member(s) have no identity on destination "
                         "provider")
parser.add_argument("--ignore-all-metadata",
                    action="store_true",
                    help="Do not set any image metadata ('properties' in Glance)")
args = parser.parse_args()

application = core.models.Application.objects.get(id=args.provider_id)