#!/usr/bin/env python
"""
Remove a bad metadata value that can prevent active
instances from being usable.
"""
import argparse

import libcloud

from core.models import Provider

from service.driver import get_admin_driver


libcloud.security.VERIFY_SSL_CERT = False
libcloud.security.VERIFY_SSL_CERT_STRICT = False


def main():
    parser = argparse.ArgumentParser(
        description="Remove any instance metadata where tmp_status is"
        + "set to networking.")
    parser.add_argument("-p",
                        "--provider",
                        required=True,
                        type=int,
                        help="Database id for a provider.")
    args = parser.parse_args()
    p = Provider.objects.get(id=args.provider)
    admin_driver = get_admin_driver(p)
    print "Retrieving all instances for %s." % (p)
    meta = admin_driver.meta(admin_driver=admin_driver)
    instances = meta.all_instances()
    bad_instances = [i for i in instances
                     if i.extra.get("metadata")
                     and i.extra["metadata"].get("tmp_status")
                     and i.extra["metadata"]["tmp_status"] == "networking"]
    for i in bad_instances:
        print "Removing networking metadata for %s" % (i)
        admin_driver._connection.ex_set_metadata(i,
                                                 {"tmp_status": ""},
                                                 replace_metadata=False)


if __name__ == "__main__":
    main()
