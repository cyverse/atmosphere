#!/usr/bin/env python
import argparse

import libcloud.security

from core.models import Identity
from service.driver import get_esh_driver
from service.instance import _update_instance_metadata
from service.tasks.driver import _deploy_init_to


libcloud.security.VERIFY_SSL_CERT = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance-uuid",help="User instance uuid that needs to be redeployed")
    parser.add_argument("--username", help="Atmosphere username")
    parser.add_argument("--provider-id", type=int, help="Atmosphere provider IDs"
                        " to use when redeploying.")
    args = parser.parse_args()
    redeploy(args.username, args.instance_uuid, args.provider_id)


def redeploy(username, instance_uuid, provider_id):
    ident = Identity.objects.get(provider__id=provider_id, created_by__username=username)
    driver = get_esh_driver(ident)
    inst = driver.get_instance(instance_uuid)
    _update_instance_metadata(driver, inst, {"tmp_status":""}, replace=False)
    _deploy_init_to(driver.__class__, driver.provider, driver.identity, inst.id, None, False)


if __name__ == "__main__":
    main()
