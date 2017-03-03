#!/usr/bin/env python

import argparse
import os
import pprint

import django; django.setup()
import core.models
import service.driver

description = """
This script makes an Application (a.k.a. image) available on a specified new
provider by doing the following:

 - Creates models (ProviderMachine, InstanceSource) in Atmosphere database
 - Transfers image data one of two ways
   - Using Glance API
   - Future coming soon: using iRODS for Atmosphere(0)
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


def main():
    args = parse_args()

    application = core.models.Application.objects.get(id=args.application_id)
    dest_provider = core.models.Provider.objects.get(id=args.provider_id)
    if args.irods_xfer:
        raise NotImplementedError("iRODS transfer not built yet")
    if args.source_provider_id:
        source_provider = core.models.Provider.objects.get(id=args.source_provider_id)
    else:
        source_provider = None

    dest_prov_acct_driver = service.driver.get_account_driver(dest_provider, raise_exception=True)
    dest_prov_img_mgr = dest_prov_acct_driver.image_manager

    # Get application owner tenant ID in destination provider
    app_creator_username = application.created_by.username
    app_creator_dest_prov_tenant = dest_prov_acct_driver.get_project(app_creator_username)
    if app_creator_dest_prov_tenant is not None:
        dest_prov_app_owner_uuid = app_creator_dest_prov_tenant.id
    else:
        if args.ignore_missing_owner:
            atmo_admin_username = dest_provider.admin.created_by.username
            dest_prov_app_owner_uuid = dest_prov_acct_driver.get_project(atmo_admin_username).id
        else:
            raise Exception("Application owner missing from destination provider, run with "
                            "--ignore-missing-owner to suppress this error (owner will "
                            "default to Atmosphere administrator")

    # Get application tags
    tags = [tag.name for tag in core.models.Tag.objects.filter(application=application)]

    # Get application members
    app_member_names = []
    if application.private is True:
        for membership in application.get_members():
            # Todo this nomenclature conflates users, groups, tenants, projects...
            member_name = membership.group.name
            member_project = dest_prov_acct_driver.get_project(member_name)
            if member_project is not None:
                # This avoids duplicates when we have both an ApplicationMembership and a ProviderMachineMembership
                if member_name not in app_member_names:
                    app_member_names.append(member_name)
            elif not args.ignore_missing_members:
                raise Exception("Application member missing from destination provider, run with "
                                "--ignore-missing-members to suppress this error")

    # Iterate over each application version
    for app_version in application.all_versions:
        provider_machines = core.models.ProviderMachine.objects.filter(application_version=app_version)
        if source_provider is not None:
            provider_machine = [pm for pm in provider_machines if pm.provider == source_provider][0]
            app_version_source_provider = source_provider
        else:
            provider_machine = provider_machines[0]
            app_version_source_provider = provider_machine.provider
        src_img_uuid = provider_machine.identifier

        src_prov_acct_driver = service.driver.get_account_driver(app_version_source_provider, raise_exception=True)
        src_prov_img_mgr = src_prov_acct_driver.image_manager

        # Get source image JSON/metadata from glance
        src_img = src_prov_img_mgr.get_image(src_img_uuid)
        pprint.pprint(src_img)

        # Todo make this idempotent
        if dest_prov_img_mgr.find_images(src_img.name):
            print("this ApplicationVersion already exists on destination provider, skipping")
            # Todo log "this ApplicationVersion already exists on destination provider, skipping"
            continue

        # Todo create new ProviderMachine and InstanceSource


        # Download image and upload to new provider
        if args.irods_xfer:
            raise NotImplementedError()
        else:
            dl_path = os.path.join('/tmp', src_img_uuid)
            src_prov_img_mgr.download_image(src_img_uuid, dl_path)
            # Todo make this idempotent (only uploads metadata if image already exists and vice versa), perhaps using this https://github.com/cyverse/atmosphere/blob/4348830fc7827fa64a08036b82e207c2e52986bd/service/openstack.py#L54
            dest_prov_img_mgr.upload_image(src_img.name, dl_path,
                                           # Glance default fields
                                           container_format=src_img.get('container_format'),
                                           disk_format=src_img.get('disk_format'),
                                           is_public=not application.private,
                                           private_user_list=app_member_names,
                                           owner=dest_prov_app_owner_uuid,
                                           tags=tags,
                                           # Atmosphere(2)-specific properties
                                           application_description=application.description,
                                           application_name=application.name,
                                           application_owner=application.created_by.username,
                                           application_tags=str(tags),
                                           application_uuid=str(application.uuid),
                                           application_version=app_version.name
                                           # Todo min_disk? min_ram?
                                           )


def parse_args():
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("application_id", type=int, help="Application ID to be migrated")
    parser.add_argument("provider_id", type=int, help="Destination provider ID")
    parser.add_argument("--source-provider-id",
                        type=int,
                        help="Migrate image from source provider with this ID (else a source provider will be chosen "
                             "automatically")
    parser.add_argument("--irods-xfer",
                        action="store_true",
                        help="Transfer image data using iRODS instead of glance download/upload "
                             "(Atmosphere(0)-specific feature)")
    parser.add_argument("--ignore-missing-owner",
                        action="store_true",
                        help="Transfer image if application owner has no identity on destination provider (owner will "
                             "be set to Atmosphere admin role")
    parser.add_argument("--ignore-missing-members",
                        action="store_true",
                        help="Transfer image if application is private and member(s) have no identity on destination "
                             "provider")
    parser.add_argument("--ignore-all-metadata",
                        action="store_true",
                        help="Do not set any image metadata ('properties' in Glance)")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
