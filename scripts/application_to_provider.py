#!/usr/bin/env python

import argparse
import hashlib
import logging
import os
import sys

import django; django.setup()
import core.models
import service.driver

description = """
This script makes an Application (a.k.a. image) available on a specified new
provider by doing any/all of the following as needed:

- Creates Glance image
- Populates Glance image metadata
- Transfers image data from existing provider
  - Image data migrated using Glance API or iRODS for Atmosphere(0)
- (Future coming soon) if Application uses an AMI-style image, ensures the
  kernel (AKI) and ramdisk (ARI) images are also present on destination
  provider, and sets appropriate properties
- Creates models (ProviderMachine, InstanceSource) in Atmosphere database

Gracefully handles the case where destination provider is already partially
populated with image data/metadata (missing information will be added).

If the application owner has no identity on the destination provider, script
will exit with error unless --ignore_missing_owner is set.

If a non-public application has or more members without identities on the
destination provider, script will exit with error unless
--ignore_missing_members is set.
"""

max_tries = 3  # Maximum number of times to attempt downloading and uploading image data


def main():
    args = _parse_args()
    logging.info("Running application_to_provider with the following arguments:\n{0}".format(str(args)))
    if args.irods_xfer:
        raise NotImplementedError("iRODS transfer not built yet")
    if args.source_provider_id == args.destination_provider_id:
        raise Exception("Source provider cannot be the same as destination provider")
    app = core.models.Application.objects.get(id=args.application_id)
    dprov = core.models.Provider.objects.get(id=args.destination_provider_id)
    if args.source_provider_id:
        sprov = core.models.Provider.objects.get(id=args.source_provider_id)
    else:
        sprov = None

    dprov_acct_driver = service.driver.get_account_driver(dprov, raise_exception=True)
    dprov_img_mgr = dprov_acct_driver.image_manager
    dprov_glance_client = dprov_img_mgr.glance

    # Get application-specific metadata from Atmosphere(2) and resolve identifiers on destination provider

    # Get application owner UUID in destination provider
    app_creator_uname = app.created_by.username
    try:
        dprov_app_owner_uuid = dprov_acct_driver.get_project(app_creator_uname, raise_exception=True).id
    except AttributeError:
        if args.ignore_missing_owner:
            dprov_atmo_admin_uname = dprov.admin.created_by.username
            dprov_app_owner_uuid = dprov_acct_driver.get_project(dprov_atmo_admin_uname).id
        else:
            raise Exception("Application owner missing from destination provider, run with "
                            "--ignore-missing-owner to suppress this error (owner will "
                            "default to Atmosphere administrator")
    # TODO convert to new string formatting style
    logging.debug("Application owner UUID in destination provider: {0}".format(dprov_app_owner_uuid))
    # If private application, get app member UUIDs in destination provider
    dprov_app_members_uuids = []
    if app.private is True:
        for membership in app.get_members():
            member_name = membership.group.name
            try:
                member_proj_uuid = dprov_acct_driver.get_project(member_name).id
                # This avoids duplicates when there is both an ApplicationMembership and a ProviderMachineMembership
                if member_proj_uuid not in dprov_app_members_uuids:
                    dprov_app_members_uuids.append(member_proj_uuid)
            except AttributeError:
                if not args.ignore_missing_members:
                    raise Exception("Application member missing from destination provider, run with "
                                    "--ignore-missing-members to suppress this error")
        logging.debug("Private app member UUIDs on destination provider: {0}".format(str(dprov_app_members_uuids)))
    # Get application tags
    app_tags = [tag.name for tag in core.models.Tag.objects.filter(application=app)]
    logging.info("Application tags: {0}".format(str(app_tags)))

    # Loop for each ApplicationVersion of the specified Application
    for app_version in app.all_versions:
        logging.info("Processing ApplicationVersion {0}".format(str(app_version)))

        # Choose/verify source provider
        existing_prov_machines = core.models.ProviderMachine.objects.filter(application_version=app_version)
        if sprov is not None:
            # Confirm given source provider has valid ProviderMachine+InstanceSource for current ApplicationVersion
            valid_sprov = False
            for provider_machine in existing_prov_machines:
                instance_source = provider_machine.instance_source
                if instance_source.provider == sprov:
                    valid_sprov = True
                    break
            if not valid_sprov:
                raise Exception("Source provider not valid for at least one version of given application")
        else:
            # Find a source provider that is not the destination provider
            for provider_machine in existing_prov_machines:
                instance_source = provider_machine.instance_source
                if instance_source.provider != dprov:
                    sprov = instance_source.provider
                    break
            if sprov is None:
                raise Exception("Could not find a source provider for at least one version of given application")
        logging.debug("Using source provider: {0}".format(sprov))

        # Get access to source provider
        sprov_img_uuid = instance_source.identifier
        sprov_acct_driver = service.driver.get_account_driver(sprov, raise_exception=True)
        sprov_img_mgr = sprov_acct_driver.image_manager
        sprov_glance_client = sprov_img_mgr.glance

        # Get source image metadata from Glance
        sprov_glance_image = sprov_glance_client.images.get(sprov_img_uuid)
        logging.debug("Source image metadata: {0}".format(str(sprov_glance_image)))

        # Check for existing ProviderMachine + InstanceSource for ApplicationVersion on destination provider
        dprov_machine = dprov_instance_source = None
        for provider_machine in existing_prov_machines:
            if provider_machine.instance_source.provider == dprov:
                dprov_machine = provider_machine
                dprov_instance_source = dprov_machine.instance_source
                logging.info("Found existing ProviderMachine and InstanceSource for image on destination provider")
        if not dprov_machine:
            logging.info("Could not find existing ProviderMachine and InstanceSource for image on destination provider"
                         ", new objects will be created")

        # Get Glance image, creating image if needed
        dprov_glance_image = None
        if dprov_instance_source is not None:
            # Todo look for matching properties application_name and application_version instead?
            if dprov_glance_client.images.get(dprov_instance_source.identifier):
                dprov_image_uuid = dprov_instance_source.identifier
                dprov_glance_image = dprov_glance_client.images.get(dprov_image_uuid)
                logging.info("Found existing Glance image, not creating a new one")
        if not dprov_glance_image:
            logging.info("Creating new Glance image")
            dprov_glance_image = dprov_glance_client.images.create()
            logging.debug("Created new empty Glance image: {0}".format(str(dprov_glance_image)))

        # Populate image metadata (this is always done)
        dprov_glance_client.images.update(dprov_glance_image.id,
                                          name=app.name,
                                          container_format=sprov_glance_image.container_format,
                                          disk_format=sprov_glance_image.disk_format,
                                          # We are using old Glance client
                                          # https://wiki.openstack.org/wiki/Glance-v2-community-image-visibility-design
                                          visibility="private" if app.private else "public",
                                          owner=dprov_app_owner_uuid,
                                          tags=app_tags,
                                          application_name=app.name,
                                          application_version=app_version.name,
                                          application_description=app.description,
                                          application_owner=app.created_by.username,  # Todo is this right?
                                          application_tags=str(app_tags),
                                          application_uuid=str(app.uuid),
                                          # Todo min_disk? min_ram? Do we care?
                                          )
        # Todo maybe not query this again, instead above, make updates to the original dprov_glance_image object
        logging.info("Populated Glance image metadata: {0}"
                     .format(str(dprov_glance_client.images.get(dprov_glance_image.id))))

        if app.private:
            # Turning generator into list so it can be searched
            dprov_img_prior_members = [m.member_id for m in dprov_glance_client.image_members.list(dprov_glance_image.id)]
            for add_member_uuid in dprov_app_members_uuids:
                if add_member_uuid not in dprov_img_prior_members:
                    dprov_glance_client.image_members.create(dprov_glance_image.id, add_member_uuid)
                else:
                    dprov_img_prior_members.remove(add_member_uuid)
            for del_member_uuid in dprov_img_prior_members:
                dprov_glance_client.image_members.delete(dprov_glance_image.id, del_member_uuid)
            logging.info("Private image updated with member UUIDs")

        # Populate image data in destination provider if needed
        if sprov_glance_image.checksum != dprov_glance_client.images.get(dprov_glance_image.id).checksum:
            logging.info("Uploading image data because checksums don't match between source and destination providers")
            local_path = os.path.join("/tmp", sprov_img_uuid)

            # Download image from source provider, only if there is no accurate local copy
            tries = 0
            while tries < max_tries:
                if os.path.exists(local_path) and file_md5(local_path) == sprov_glance_image.checksum:
                    logging.debug("Verified correct local copy of the image")
                    break
                else:
                    if tries != 0:
                        logging.warning("Image data download attempt failed")
                    tries += 1
                    logging.debug("Attempting to download image data from source provider")
                    image_data = sprov_glance_client.images.data(sprov_img_uuid)
                    with open(local_path, 'wb') as img_file:
                        for chunk in image_data:
                            img_file.write(chunk)

            if file_md5(local_path) != sprov_glance_image.checksum:
                raise Exception("Could not download Glance image from source provider")

            # Upload image to destination provider, keep trying until checksums match
            tries = 0
            while tries < max_tries:
                tries += 1
                logging.debug("Attempting to upload image data to destination provider")
                with open(local_path, 'rb') as img_file:
                    dprov_glance_client.images.upload(dprov_glance_image.id, img_file)
                if sprov_glance_image.checksum != dprov_glance_client.images.get(dprov_glance_image.id).checksum:
                    logging.info("Successfully uploaded image data to destination provider")
                    break
                else:
                    logging.warning("Image data upload attempt failed")

            if sprov_glance_image.checksum != dprov_glance_client.images.get(dprov_glance_image.id).checksum:
                raise Exception("Could not successfully upload image data")

            if not args.keep_local_cache:
                logging.debug("Removing local cache of image data")
                os.remove(local_path)

        # Create models in database
        if not (dprov_machine or dprov_instance_source):
            logging.info("Creating new ProviderMachine and InstanceSource")
            dprov_instance_source = core.models.InstanceSource(provider=dprov,
                                                               identifier=dprov_glance_image.id,
                                                               created_by=app.created_by,
                                                               # Todo created_by_identity, start_date, end_date?
                                                               )
            dprov_instance_source.save()
            dprov_machine = core.models.ProviderMachine(application_version=app_version,
                                                        instance_source=dprov_instance_source)
            dprov_machine.save()


def file_md5(path):
    # https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _parse_args():
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("application_id", type=int, help="Application ID to be migrated")
    parser.add_argument("destination_provider_id", type=int, help="Destination provider ID")
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
    parser.add_argument("--keep-local-cache",
                        action="store_true",
                        help="Keep locally cached copies of image data - speeds up subsequent runs for same "
                             "application but may consume a lot of storage space in /tmp")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    # Todo should we get a particular logger?
    try:
        main()
    except Exception as e:
        logging.exception(e)
        raise
