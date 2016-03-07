#!/usr/bin/env python
import argparse
import subprocess
import logging

from django.utils.timezone import datetime, utc
from service.driver import get_account_driver
from core.models import Provider, ProviderMachine, Identity, MachineRequest, Application, ProviderMachine
from core.models.application import _generate_app_uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use.")
    parser.add_argument("--image_ids",
                        help="Image ID(s) to be repaired. (Comma-Separated)")
    args = parser.parse_args()
    if not args.provider:
        raise Exception("Required argument 'provider' is missing. Please provide the DB ID of the provider to continue.")
    else:
        provider = Provider.objects.get(id=args.provider)
    images = args.image_ids.split(",")
    fix_images(provider, images)


def fix_images(provider, images=[]):
    accounts = get_account_driver(provider)
    for image_id in images:
        glance_image = accounts.image_manager.get_image(image_id)
        if not glance_image:
            print "ERROR: Image %s does not exist." % image_id
            break
        try:
            # NOTE: Will need to change provider query when migrating to DD and
            # beyond
            pm = ProviderMachine.objects.get(
                provider=provider,
                identifier=image_id)
        except ProviderMachine.DoesNotExist:
            print "Error: NO ProviderMachine for Provider:%s Image ID:%s" % (provider, image_id)
            break
        # It's a real image. It SHOULD have a corresponding machine request
        try:
            mr = MachineRequest.objects.get(new_machine__identifier=image_id)
        except MachineRequest.DoesNotExist:
            print "Warn: MachineRequest by this ID could not be found"
            mr = None
        current_application = pm.application
        uuid = _generate_app_uuid(image_id)
        try:
            original_application = Application.objects.get(uuid=uuid)
        except Application.DoesNotExist:
            print "ProviderMachine %s is an update to Application: %s" % (pm, current_application)
            print "Creating seperate Application for ProviderMachine %s" % pm
            original_application = _create_new_application(mr, image_id)
        # Update Application from MachineRequest information
        if mr:
            original_application = _update_application(
                original_application,
                mr)

        if original_application.uuid is not current_application.uuid:
            pm.application = original_application
            pm.save()

        # Write to metadata INCLUDING kernel and ramdisk id!
        fix_image_metadata(accounts, glance_image, original_application, mr)


def fix_image_metadata(accounts, glance_image, application, machine_request):
    if not accounts:
        raise Exception("FATAL - No Account Driver!")
    elif not glance_image:
        raise Exception("FATAL - No glance image!")
    # Start with ALL the information
    image_id = glance_image.id
    updates = glance_image.properties
    # Look for kernel and ramdisk
    if 'kernel_id' not in glance_image.properties\
            or 'ramdisk_id' not in glance_image.properties:
        print "Image %s is missing kernel and/or ramdisk ..." % (image_id,),
        updates['kernel_id'], updates['ramdisk_id'] = find_kernel_ramdisk(
            accounts, machine_request)
        if not updates['kernel_id'] or not updates['ramdisk_id']:
            raise Exception(
                "FATAL - no Kernel/Ramdisk found for image %s" %
                image_id)
    # Update the meta description (all other values should be fine)
    meta_description = updates.get("application_description")
    if "\n" in application.description or meta_description != application.description:
        print "Image Metadata Description: %s differs from Application Description:%s" % (meta_description, application.description)
        updates["application_description"] = application.description
    print "Updating glance image %s properties: %s" % (image_id, updates)
    glance_image.update(properties=updates)


def find_kernel_ramdisk(accounts, machine_request):
    print "Pass #1. Does my ancestor have a kernel or ramdisk?",
    if not machine_request:
        print " FAIL! MachineRequest does not exist."
        return None, None
    else:
        print "Looking up Kernel/ramdisk for: %s" % machine_request.new_machine
        old_pm = machine_request.instance.provider_machine
        old_glance_image = accounts.image_manager.get_image(old_pm.identifier)
        if not old_glance_image:
            print " Fail! Old image:%s Did NOT exist in the cloud." % old_pm.identifier
            return None, None
        elif 'kernel_id' in old_glance_image.properties and 'ramdisk_id' in old_glance_image.properties:
            kernel = old_glance_image.properties['kernel_id']
            ramdisk = old_glance_image.properties['ramdisk_id']
            print " Success! Kernel:%s Ramdisk:%s FOUND!" % (kernel, ramdisk)
            return kernel, ramdisk
        else:
            print " Fail! Old Image:%s ALSO missing kernel+ramdisk" % old_glance_image
        try:
            existing_parent_request = MachineRequest.objects.get(
                new_machine__identifier=image_id)
        except MachineRequest.DoesNotExist:
            print "ALSO: MachineRequest for parent could not be found! FAIL!"
            return None, None
        print " Re-testing old image to check THEIR parent!"
        return find_kernel_ramdisk(accounts, existing_parent_request)
    # Fall through and exit, failure occurred.
    return None, None


def _update_parent_application(machine_request, new_image_id, tags=[]):
    parent_app = machine_request.instance.source.providermachine.application
    return _update_application(parent_app, machine_request, tags=tags)


def _update_application(application, machine_request, tags=[]):
    if application.name is not machine_request.new_application_name:
        application.name = machine_request.new_application_name
    if machine_request.new_application_description:
        application.description = machine_request.new_application_description
    application.private = not machine_request.is_public()
    application.tags = tags
    application.save()
    return application


if __name__ == "__main__":
    main()
