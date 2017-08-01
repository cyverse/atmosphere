#!/usr/bin/env python

import argparse
import hashlib
import json
import logging
import os
import sys
import urlparse

import OpenSSL.SSL

from irods.session import iRODSSession
import glanceclient.exc
import django; django.setup()
import core.models
import service.driver
from chromogenic.clean import mount_and_clean
from rtwo.drivers.common import _connect_to_glance
from atmosphere.settings import secrets

description = """
This script makes an Application (a.k.a. image) available on a specified new
provider by doing any/all of the following as needed:

- Creates Glance image
- Populates Glance image metadata
- Optionally, uses Chromogenic library to remove undesired state from images
  which were created from Atmosphere(1) instances
- Transfers image data from existing provider to new provider, one of two ways:
  - Using Glance API (default)
  - Using iRODS (Atmosphere(0)-specific feature), see below
- If Application uses an AMI-style image, ensures the
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

## iRODS Transfer Information

The iRODS transfer feature was developed for CyVerse Atmosphere(0); may be of
limited use elsewhere. In order to use it:
- Source and destination providers must use the iRODS storage backend for
  OpenStack Glance (https://github.com/cyverse/glance-irods)
- Src. and dst. providers must store images in the same iRODS zone
- --source-provider-id, --irods-conn, --irods-src-coll, and --irods-dst-coll
  must all be defined
- Credentials passed in --irods-conn must have write access to both source and
  destination collections
- --clean cannot be used with iRODS transfer

Considerations when using iRODS transfer:
- The credentials passed in --irods-conn will be used to populate the image
  location in the Glance database on the destination provider. Consider passing
  the iRODS credentials already in use for the Glance iRODS back-end on that
  provider, and making the source collection readable to same.
- This script does not set data object permissions in iRODS. This means that
  for the destination provider, the iRODS account used by Glance server should
  have write (or own) access to the destination collection (where new data
  objects are created), and *inheritance should be enabled*.
- When using iRODS transfer, the Glance image object in the destination provider
  will not have a checksum (will be "None"). This is a known issue in Glance:
  https://bugs.launchpad.net/glance/+bug/1551498
"""

max_tries = 3  # Maximum number of times to attempt downloading and uploading image data


def _parse_args():
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("application_id", type=int, help="Application ID to be migrated")
    parser.add_argument("destination_provider_id", type=int, help="Destination provider ID")
    parser.add_argument("--source-provider-id",
                        type=int,
                        help="Migrate image from source provider with this ID (else a source provider will be chosen "
                             "automatically")
    parser.add_argument("--metadata-only",
                        action="store_true",
                        help="Only migrate/update image metadata, not image data")
    parser.add_argument("--ignore-missing-owner",
                        action="store_true",
                        help="Transfer image if application owner has no identity on destination provider (owner will "
                             "be set to Atmosphere admin role")
    parser.add_argument("--ignore-missing-members",
                        action="store_true",
                        help="Transfer image if application is private and member(s) have no identity on destination "
                             "provider")
    parser.add_argument("--migrate-end-dated-versions",
                        action="store_true",
                        help="Migrate all ApplicationVersions, even those that have been end dated")
    parser.add_argument("--clean",
                        action="store_true",
                        help="Use Chromogenic library to remove undesired state from images which were created from "
                             "Atmosphere(1) instances (cannot be used with iRODS transfer)")
    parser.add_argument("--persist-local-cache",
                        action="store_true",
                        help="If image download succeeds but upload fails, keep local cached copy for subsequent "
                             "attempt. (Local cache is always deleted after successful upload). "
                             "May consume a lot of disk space.")
    parser.add_argument("--src-glance-client-version",
                        type=int,
                        help="Glance client version to use for source provider")
    parser.add_argument("--dst-glance-client-version",
                        type=int,
                        help="Glance client version to use for destination provider")
    parser.add_argument("--irods-conn",
                        type=str, metavar="irods://user:password@host:port/zone",
                        help="iRODS connection string in the form of irods://user:password@host:port/zone")
    parser.add_argument("--irods-src-coll",
                        type=str, metavar="/myzone/foo",
                        help="Path to collection for iRODS images on source provider")
    parser.add_argument("--irods-dst-coll",
                        type=str, metavar="/myzone/bar",
                        help="Path to collection for iRODS images on destination provider")
    args = parser.parse_args()
    return args


def main(application_id,
         destination_provider_id,
         source_provider_id=None,
         metadata_only=False,
         ignore_missing_owner=False,
         ignore_missing_members=False,
         migrate_end_dated_versions=False,
         clean=False,
         persist_local_cache=False,
         src_glance_client_version=None,
         dst_glance_client_version=None,
         irods_conn_str=None,
         irods_src_coll=None,
         irods_dst_coll=None,
         ):

    irods_args = (irods_conn_str, irods_src_coll, irods_dst_coll)
    if clean and any(irods_args):
        raise Exception("--clean cannot be used with iRODS transfer mode")
    if any(irods_args):
        irods = True
        if all(irods_args) and source_provider_id:
            irods_conn = _parse_irods_conn(irods_conn_str)
        else:
            raise Exception("If using iRODS transfer then --source-provider-id, --irods-conn, --irods-src-coll, and "
                            "--irods-dst-coll must all be defined")
    else:
        irods = False
        irods_conn = irods_src_coll = irods_dst_coll = None

    if source_provider_id == destination_provider_id:
        raise Exception("Source provider cannot be the same as destination provider")
    app = core.models.Application.objects.get(id=application_id)
    dprov = core.models.Provider.objects.get(id=destination_provider_id)
    if source_provider_id:
        sprov = core.models.Provider.objects.get(id=source_provider_id)
    else:
        sprov = None

    dprov_acct_driver = service.driver.get_account_driver(dprov, raise_exception=True)
    if dst_glance_client_version:
        dprov_keystone_client = dprov_acct_driver.image_manager.keystone
        dprov_glance_client = _connect_to_glance(dprov_keystone_client, version=dst_glance_client_version)
    else:
        dprov_glance_client = dprov_acct_driver.image_manager.glance

    dprov_atmo_admin_uname = dprov.admin.project_name()
    dprov_atmo_admin_uuid = dprov_acct_driver.get_project(dprov_atmo_admin_uname).id

    # Get application-specific metadata from Atmosphere(2) and resolve identifiers on destination provider

    # Get application owner UUID in destination provider
    app_creator_uname = app.created_by_identity.project_name()
    try:
        dprov_app_owner_uuid = dprov_acct_driver.get_project(app_creator_uname, raise_exception=True).id
    except AttributeError:
        if ignore_missing_owner:
            dprov_app_owner_uuid = dprov_atmo_admin_uuid
        else:
            raise Exception("Application owner missing from destination provider, run with "
                            "--ignore-missing-owner to suppress this error (owner will "
                            "default to Atmosphere administrator")
    logging.debug("Application owner UUID in destination provider: {0}".format(dprov_app_owner_uuid))

    # If private application, get app member UUIDs in destination provider
    dprov_app_members_uuids = []
    if app.private is True:
        dprov_app_members_uuids.append(dprov_atmo_admin_uuid)  # Atmosphere administrator is always a member
        for membership in app.get_members():
            member_name = membership.group.name
            try:
                member_proj_uuid = dprov_acct_driver.get_project(member_name).id
                # This avoids duplicates when there is both an ApplicationMembership and a ProviderMachineMembership
                if member_proj_uuid not in dprov_app_members_uuids:
                    dprov_app_members_uuids.append(member_proj_uuid)
            except AttributeError:
                if not ignore_missing_members:
                    raise Exception("Application member missing from destination provider, run with "
                                    "--ignore-missing-members to suppress this error")
        logging.debug("Private app member UUIDs on destination provider: {0}".format(str(dprov_app_members_uuids)))

    # Get application tags
    app_tags = [tag.name for tag in core.models.Tag.objects.filter(application=app)]
    logging.info("Application tags: {0}".format(str(app_tags)))

    # Loop for each ApplicationVersion of the specified Application
    if migrate_end_dated_versions:
        versions = app.all_versions()
    else:
        versions = app.active_versions()
    for app_version in versions:
        logging.info("Processing ApplicationVersion {0}".format(str(app_version)))

        # Choose/verify source provider
        existing_prov_machines = core.models.ProviderMachine.objects.filter(application_version=app_version)
        if sprov is not None:
            # Confirm given source provider has valid ProviderMachine+InstanceSource for current ApplicationVersion
            valid_sprov = False
            for provider_machine in existing_prov_machines:
                sprov_instance_source = provider_machine.instance_source
                if sprov_instance_source.provider == sprov:
                    valid_sprov = True
                    break
            if not valid_sprov:
                raise Exception("Source provider not valid for at least one version of given application")
        else:
            # Find a source provider that is not the destination provider
            for provider_machine in existing_prov_machines:
                sprov_instance_source = provider_machine.instance_source
                if sprov_instance_source.provider != dprov:
                    sprov = sprov_instance_source.provider
                    break
            if sprov is None:
                raise Exception("Could not find a source provider for at least one version of given application")
        logging.debug("Using source provider: {0}".format(sprov))

        # Get access to source provider
        sprov_img_uuid = sprov_instance_source.identifier
        
        sprov_acct_driver = service.driver.get_account_driver(sprov, raise_exception=True)
        if src_glance_client_version:
            sprov_keystone_client = service.driver.get_account_driver(sprov, raise_exception=True)
            sprov_glance_client = _connect_to_glance(sprov_keystone_client, version=src_glance_client_version)
        else:
            sprov_glance_client = sprov_acct_driver.image_manager.glance

        # Get source image metadata from Glance, and determine if image is AMI-based
        sprov_glance_image = sprov_glance_client.images.get(sprov_img_uuid)
        if sprov_glance_image.get("kernel_id") or sprov_glance_image.get("ramdisk_id"):
            if sprov_glance_image.get("kernel_id") and sprov_glance_image.get("ramdisk_id"):
                ami = True
            else:
                raise Exception("AMI-based image must have both a kernel_id and ramdisk_id defined")
        else:
            ami = False
        # If AMI-based image, verify that AKI and ARI images actually exist in source provider
        if ami:
            try:
                sprov_aki_glance_image = sprov_glance_client.images.get(sprov_glance_image.get("kernel_id"))
                sprov_ari_glance_image = sprov_glance_client.images.get(sprov_glance_image.get("ramdisk_id"))
            except glanceclient.exc.HTTPNotFound:
                logging.critical("Could not retrieve the AKI or ARI image on source provider, for an AMI-based image")

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

        # Get or create Glance image
        """
        todo corner case: we have existing InstanceSource with wrong image UUID?
        Do we correct it later (good) or end up creating a duplicate (maybe bad)?
        this logic may also need refactor
        """
        dprov_glance_image = get_or_create_glance_image(dprov_glance_client, sprov_img_uuid)

        # Get or create AKI+ARI Glance images for AMI-based image
        if ami:
            dprov_aki_glance_image = get_or_create_glance_image(dprov_glance_client,
                                                                sprov_glance_image.get("kernel_id"))
            dprov_ari_glance_image = get_or_create_glance_image(dprov_glance_client,
                                                                sprov_glance_image.get("ramdisk_id"))

        # Create models in database
        if not (dprov_machine or dprov_instance_source):
            logging.info("Creating new ProviderMachine and InstanceSource")
            dprov_instance_source = core.models.InstanceSource(provider=dprov,
                                                               identifier=dprov_glance_image.id,
                                                               created_by=app.created_by,
                                                               end_date=sprov_instance_source.end_date
                                                               )
            dprov_instance_source.save()
            dprov_machine = core.models.ProviderMachine(application_version=app_version,
                                                        instance_source=dprov_instance_source)
            dprov_machine.save()

        # Populate image metadata (this is always done)
        if dst_glance_client_version == 1:
            dprov_glance_client.images.update(dprov_glance_image.id,
                                              name=app.name,
                                              container_format="ami" if ami else sprov_glance_image.container_format,
                                              disk_format="ami" if ami else sprov_glance_image.disk_format,
                                              is_public=False if app.private else True,
                                              owner=dprov_app_owner_uuid,
                                              properties=dict(
                                                  tags=app_tags,
                                                  application_name=app.name,
                                                  application_version=app_version.name,
                                                  # Glance v1 client throws exception on line breaks
                                                  application_description=app.description
                                                      .replace('\r', '').replace('\n', ' -- '),
                                                  application_owner=app_creator_uname,
                                                  application_tags=json.dumps(app_tags),
                                                  application_uuid=str(app.uuid))
                                                  # Todo min_disk? min_ram? Do we care?
                                              )
            if ami:
                dprov_glance_client.images.update(dprov_glance_image.id,
                                                  properties=dict(
                                                      kernel_id=sprov_glance_image.kernel_id,
                                                      ramdisk_id=sprov_glance_image.ramdisk_id)
                                                  )
        else:
            dprov_glance_client.images.update(dprov_glance_image.id,
                                              name=app.name,
                                              container_format="ami" if ami else sprov_glance_image.container_format,
                                              disk_format="ami" if ami else sprov_glance_image.disk_format,
                                              visibility="private" if app.private else "public",
                                              owner=dprov_app_owner_uuid,
                                              tags=app_tags,
                                              application_name=app.name,
                                              application_version=app_version.name,
                                              application_description=app.description,
                                              application_owner=app_creator_uname,
                                              application_tags=json.dumps(app_tags),
                                              application_uuid=str(app.uuid),
                                              # Todo min_disk? min_ram? Do we care?
                                              )
            if ami:
                dprov_glance_client.images.update(dprov_glance_image.id,
                                                  kernel_id=sprov_glance_image.kernel_id,
                                                  ramdisk_id=sprov_glance_image.ramdisk_id)
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

        # If AMI-based image, set metadata for AKI and ARI images
        if ami:
            dprov_glance_client.images.update(sprov_aki_glance_image.id,
                                              container_format="aki",
                                              disk_format="aki",
                                              visibility="public",
                                              name=sprov_aki_glance_image.name,
                                              owner=dprov_atmo_admin_uuid,
                                              )
            dprov_glance_client.images.update(sprov_ari_glance_image.id,
                                              container_format="ari",
                                              disk_format="ari",
                                              visibility="public",
                                              name=sprov_ari_glance_image.name,
                                              owner=dprov_atmo_admin_uuid,
                                              )

        if not metadata_only:
            local_storage_dir = secrets.LOCAL_STORAGE if os.path.exists(secrets.LOCAL_STORAGE) else "/tmp"
            local_path = os.path.join(local_storage_dir, sprov_img_uuid)

            # Populate image data in destination provider if needed
            migrate_or_verify_image_data(sprov_img_uuid, sprov_glance_client, dprov_glance_client, local_path,
                                         persist_local_cache, irods, irods_conn, irods_src_coll, irods_dst_coll,
                                         clean=True if clean else False,
                                         dst_glance_client_version=dst_glance_client_version)
            # If AMI-based image, populate image data in destination provider if needed
            if ami:
                migrate_or_verify_image_data(sprov_aki_glance_image.id, sprov_glance_client, dprov_glance_client,
                                             local_path, persist_local_cache, irods, irods_conn, irods_src_coll,
                                             irods_dst_coll, dst_glance_client_version=dst_glance_client_version)
                migrate_or_verify_image_data(sprov_ari_glance_image.id, sprov_glance_client, dprov_glance_client,
                                             local_path, persist_local_cache, irods, irods_conn, irods_src_coll,
                                             irods_dst_coll, dst_glance_client_version=dst_glance_client_version)


def file_md5(path):
    # https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_or_create_glance_image(glance_client, img_uuid):
    """
    Given a glance_client object and a desired img_uuid, either gets the existing image or creates a new one
    Returns a glance_client image object
    """
    try:
        glance_image = glance_client.images.get(img_uuid)
    except glanceclient.exc.HTTPConflict:
        raise Exception("Could not create Glance image with specified UUID, possibly because there is already a "
                        "deleted image with the same UUID stored in the destination provider. If this is the case "
                        "(look in Glance database on destination provider), then run a `glance-manage db purge` to "
                        "free up the UUID.")
    except glanceclient.exc.HTTPNotFound:
        logging.debug("Could not locate glance image in specified provider")
        logging.info("Creating new Glance image")
        return glance_client.images.create(id=img_uuid)
    else:
        if glance_image is not None:
            logging.info("Found Glance image matching specified UUID {0}, re-using it".format(img_uuid))
            return glance_image


def migrate_or_verify_image_data(img_uuid, src_glance_client, dst_glance_client, local_path, persist_local_cache, irods,
                                 irods_conn, irods_src_coll, irods_dst_coll, clean=False,
                                 dst_glance_client_version=None):
    """
    Migrates or verifies Glance image data between a source and destination provider, depending on image status
    in destination provider.
    - If image is in a queued state (accepting new data), migrates image data using either Glance API download/upload or
      iRODS data object copy.
    - If image is in an active state, attempts to verify image data matches using checksum or size
    - If image is in any other state, it is not usable, raises an exception

    Args:
        img_uuid: UUID of image to be migrated
        src_glance_client: glance client object for source provider
        dst_glance_client: glance client object for destination provider
        local_path: Local storage path
        persist_local_cache: If image download succeeds but upload fails, keep local cached copy for subsequent attempt
                             (Local cache is always deleted after successful upload)
        irods: boolean True if using iRODS for image transfer, false if using pure Glance API
        irods_conn: dict as returned by _parse_irods_conn()
        irods_src_coll: Path to collection for iRODS images on source provider
        irods_dst_coll: Path to collection for iRODS images on destination provider
        clean: apply Chromogenic mount_and_clean() to downloaded image

    Returns: True if successful, else raises exception
    """

    src_img = src_glance_client.images.get(img_uuid)
    dst_img = dst_glance_client.images.get(img_uuid)

    if dst_img.status == "queued":
        if irods:
            migrate_image_data_irods(dst_glance_client, irods_conn, irods_src_coll, irods_dst_coll, img_uuid, dst_glance_client_version)
        else:
            migrate_image_data_glance(src_glance_client, dst_glance_client, img_uuid, local_path, persist_local_cache,
                                      clean=clean)
    elif dst_img.status == "active":
        if irods:
            if src_img.size != dst_img.size:
                logging.warn("Warning: image data already present on destination provider but size does not match; "
                             "this may be OK if image was previously migrated with --clean")
        else:
            if src_img.checksum != dst_img.checksum:
                logging.warn("Warning: image data already present on destination provider but checksum does not "
                             "match; this may be OK if image was previously migrated with --clean, or if iRODS "
                             "transfer was previously used to migrate image")
    else:
        raise Exception("Glance image on destination provider is not in an uploadable or usable status")
    return True


def migrate_image_data_glance(src_glance_client, dst_glance_client, img_uuid, local_path, persist_local_cache=True,
                              max_tries=3, clean=False):
    """
    Migrates image data using Glance API. Assumes that:
    - The Glance image object has already been created in the source provider
    - The Glance image UUIDs match between providers

    Args:
        src_glance_client: glance client object for source provider
        dst_glance_client: glance client object for destination provider
        img_uuid: UUID of image to be migrated
        local_path: Local storage path
        persist_local_cache: If image download succeeds but upload fails, keep local cached copy for subsequent attempt
                             (Local cache is always deleted after successful upload)
        max_tries: number of times to attempt each of download and upload
        clean: apply Chromogenic mount_and_clean() to downloaded image

    Returns: True if success, else raises an exception
    """
    src_img = src_glance_client.images.get(img_uuid)

    # Download image from source provider, only if there is no correct local copy
    if os.path.exists(local_path) and file_md5(local_path) == src_img.checksum:
        logging.debug("Verified correct local copy of the image")
    else:
        tries = 0
        while tries < max_tries:
            tries += 1
            logging.debug("Attempting to download image data from source provider")
            image_data = src_glance_client.images.data(img_uuid)
            with open(local_path, 'wb') as img_file:
                for chunk in image_data:
                    img_file.write(chunk)
            if os.path.exists(local_path) and file_md5(local_path) == src_img.checksum:
                logging.debug("Image data download succeeded")
                break
            else:
                logging.warning("Image data download attempt failed")
        if file_md5(local_path) != src_img.checksum:
            if not persist_local_cache:
                os.remove(local_path)
            raise Exception("Could not download Glance image from source provider")

    if clean:
        # TODO is this a reasonable mount point or should we create one in /tmp?
        mount_and_clean(local_path, "/mnt")
        logging.info("Cleaned image using Chromogenic")
    local_img_checksum = file_md5(local_path)

    # Upload image to destination provider, keep trying until checksums match
    tries = 0
    while tries < max_tries:
        tries += 1
        logging.debug("Attempting to upload image data to destination provider")
        with open(local_path, 'rb') as img_file:
            try:
                dst_glance_client.images.upload(img_uuid, img_file)
                if local_img_checksum == dst_glance_client.images.get(img_uuid).checksum:
                    logging.info("Successfully uploaded image data to destination provider")
                    break
                else:
                    logging.warning("Image data upload attempt failed")
            except OpenSSL.SSL.SysCallError:
                logging.warning("Image data upload attempt failed")

    if local_img_checksum != dst_glance_client.images.get(img_uuid).checksum:
        raise Exception("Image checksums don't match, upload may have failed!")
    else:
        os.remove(local_path)
        return True


def migrate_image_data_irods(dst_glance_client, irods_conn, irods_src_coll, irods_dst_coll, img_uuid,
                             dst_glance_client_version=None):
    """
    Migrates image data using iRODS and then sets image location using Glance API.

    Args:
        dst_glance_client: glance client object for destination provider
        irods_conn: dict as returned by _parse_irods_conn()
        irods_src_coll: Path to collection for iRODS images on source provider
        irods_dst_coll: Path to collection for iRODS images on destination provider
        img_uuid: UUID of image to be migrated

    Returns: True if successful, else raises exception
    """
    sess = iRODSSession(host=irods_conn.get('host'),
                        port=irods_conn.get('port'),
                        zone=irods_conn.get('zone'),
                        user=irods_conn.get('username'),
                        password=irods_conn.get('password'))
    src_data_obj_path = os.path.join(irods_src_coll, img_uuid)
    dst_data_obj_path = os.path.join(irods_dst_coll, img_uuid)
    print(src_data_obj_path, dst_data_obj_path)
    sess.data_objects.copy(src_data_obj_path, dst_data_obj_path)
    logging.info("Copied image data to destination collection in iRODS")
    dst_img_location = "irods://{0}:{1}@{2}:{3}{4}".format(
        irods_conn.get('username'),
        irods_conn.get('password'),
        irods_conn.get('host'),
        irods_conn.get('port'),
        dst_data_obj_path
    )
    # Assumption that iRODS copy will always be correct+complete, not inspecting checksums afterward?
    if int(dst_glance_client_version) == 1:
        dst_glance_client.images.update(img_uuid, location=dst_img_location)
    else:
        dst_glance_client.images.add_location(img_uuid, dst_img_location, dict())
    logging.info("Set image location in Glance")
    return True


def _parse_irods_conn(irods_conn_str):
    u = urlparse.urlparse(irods_conn_str)
    irods_conn = {"username": u.username, "password": u.password, "host": u.hostname, "port": u.port, "zone": u.path[1:]}
    return irods_conn


if __name__ == "__main__":
    # Spit log messages to stdout
    output = logging.StreamHandler(sys.stdout)
    output.setLevel(logging.DEBUG)
    output.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(output)
    # Todo should we use a particular logger?
    try:
        args = _parse_args()
        logging.info("Running application_to_provider with the following arguments:\n{0}".format(str(args)))
        main(args.application_id,
             args.destination_provider_id,
             source_provider_id=args.source_provider_id,
             metadata_only=args.metadata_only,
             ignore_missing_owner=args.ignore_missing_owner,
             ignore_missing_members=args.ignore_missing_members,
             migrate_end_dated_versions=args.migrate_end_dated_versions,
             clean=args.clean,
             persist_local_cache=args.persist_local_cache,
             src_glance_client_version=args.src_glance_client_version,
             dst_glance_client_version=args.dst_glance_client_version,
             irods_conn_str=args.irods_conn,
             irods_src_coll=args.irods_src_coll,
             irods_dst_coll=args.irods_dst_coll)
    except Exception as e:
        logging.exception(e)
        raise
