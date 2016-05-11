#!/usr/bin/env python
import argparse
import subprocess
import logging

import django; django.setup()

from service.accounts.openstack_manager import AccountDriver as OSAccountDriver
from core.models import Provider, Identity, MachineRequest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use.")
    parser.add_argument("image_ids",
                        help="Image ID(s) to be repaired. (Comma-Separated)")
    args = parser.parse_args()

    if not args.provider:
        provider = Provider.objects.get(location='iPlant Cloud - Tucson')
    else:
        provider = Provider.objects.get(id=args.provider)
    images = args.image_ids.split(",")

    accounts = OSAccountDriver(provider)
    for image_id in images:
        mr = MachineRequest.objects.get(new_machine__instance_source__identifier=image_id)
        glance_image = accounts.get_image(image_id)
        if hasattr(glance_image, 'properties'):
            glance_image_properties = glance_image.properties
        else:
            glance_image_properties = dict(glance_image.items())
        if 'kernel_id' not in glance_image_properties\
                or 'ramdisk_id' not in glance_image_properties:
            print "Image %s (%s) is missing kernel and/or ramdisk ..." % (image_id, glance_image.name),
            fix_image(accounts, glance_image, mr)


def fix_image(accounts, glance_image, mr):
    old_machine_id = mr.instance.provider_machine.identifier
    old_glance_image = accounts.get_image(old_machine_id)
    if hasattr(old_glance_image, 'properties'):
        old_glance_image_properties = old_glance_image.properties
    else:
        old_glance_image_properties = dict(old_glance_image.items())
    if 'kernel_id' not in old_glance_image_properties\
            or 'ramdisk_id' not in old_glance_image_properties:
        print "Parent image %s (%s) is also missing kernel/ramdisk. OK!"\
            % (old_machine_id, old_glance_image.name)
        return
    old_kernel = old_glance_image_properties['kernel_id']
    old_ramdisk = old_glance_image_properties['ramdisk_id']
    print "Parent image %s (%s) contains kernel (%s) and ramdisk (%s). FIX POSSIBLE!"\
        % (old_machine_id, old_glance_image.name, old_kernel, old_ramdisk)
    accounts.image_manager.update_image(
        glance_image,
        kernel_id=old_kernel, ramdisk_id=old_ramdisk)
    print "Fixed"


if __name__ == "__main__":
    main()
