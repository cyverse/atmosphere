#!/usr/bin/env python
import argparse
from traceback import print_exc

from api import get_esh_driver

from core.models import Provider, Identity

from service.instance import suspend_instance, resume_instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True,
                        help="Username that instance belongs to.")
    parser.add_argument("--provider", type=int, required=True,
                        help="Provider instance is running in.")
    parser.add_argument("--instance", required=True,
                        help="OpenStack instance id.")
    args = parser.parse_args()
    user = args.user
    instance = args.instance
    provider = args.provider
    ident = Identity.objects.get(provider__id=provider, created_by__username=user)
    driver = get_esh_driver(ident)
    inst = driver.get_instance(instance)
    try:
        suspend_instance(driver, inst, ident.provider.id, ident.id, ident.created_by)
    except as e:
        print("Suspend failed.")
        print_exc()


if __name__ == "__main__":
    main()
