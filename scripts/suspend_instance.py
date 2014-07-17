#!/usr/bin/env python
import argparse
import sys
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
    parser.add_argument("--resume", action="store_true",
                        help="Resume the instance instead of suspending it.")
    args = parser.parse_args()
    user = args.user
    instance = args.instance
    provider = args.provider
    try:
        ident = Identity.objects.get(provider__id=provider, created_by__username=user)
    except Exception as e:
        print("Identity could not be found for user: %s on provider: %s" % (user, provider))
        print_exc()
        return 1
    driver = get_esh_driver(ident)
    try:
        inst = driver.get_instance(instance)
    except Exception as e:
        print("Instance %s was not found." % (instance))
        print_exc()
        return 2
    if args.resume:
        try:
            resume_instance(driver, inst, ident.provider.id, ident.id, ident.created_by)
        except Exception as e:
            print("Resume failed.")
            print("Calling service.instance.resume_instance failed for instance %s." % (instance))
            print_exc()
            return 3
        print("Resumed %s." % (instance))
    else:
        try:
            suspend_instance(driver, inst, ident.provider.id, ident.id, ident.created_by)
        except Exception as e:
            print("Suspend failed.")
            print("Calling service.instance.suspend_instance failed for instance %s." % (instance))
            print_exc()
            return 4
        print("Suspended %s." % (instance))
    return 0

if __name__ == "__main__":
    sys.exit(main())
