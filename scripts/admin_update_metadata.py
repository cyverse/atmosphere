#!/usr/bin/env python
import argparse

import django
django.setup()

from service.openstack import glance_write_machine
from core.models import ProviderMachine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID"
                        " to use.")
    parser.add_argument("image_ids", nargs="?",
                        help="Image ID(s) to be renamed. (Comma-Separated)")
    args = parser.parse_args()

    if not args.provider:
        return parser.print_help()

    all_images = ProviderMachine.objects.filter(
        instance_source__provider_id=args.provider)
    if args.image_ids:
        all_images = all_images.filter(
            instance_source__identifier__in=args.image_ids.split(','))

    for provider_machine in all_images:
        glance_write_machine(provider_machine)
        print "Updated metadata for %s" % (provider_machine,)

if __name__ == "__main__":
    main()
