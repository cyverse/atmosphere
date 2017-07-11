#!/usr/bin/env python

import argparse
import logging
import sys

import application_to_provider
# Needed?
# import django; django.setup()
import core.models

description = """
This script effects a one-way synchronization of Applications (a.k.a. images)
from a master Provider to one or more replica Providers.
"""


def main(master_provider_id, replica_provider_ids, dry_run=False):

    if dry_run:
        import pprint
        pprint.pprint(args)
        dry_run_output = []

    # Sanity checking
    for id in replica_provider_ids:
        if id == master_provider_id:
            raise Exception("Master provider cannot also be a replica")
    if len(replica_provider_ids) > len(set(replica_provider_ids)):
        raise Exception("No duplicate replica providers allowed")

    # Resolve providers
    master_prov = core.models.Provider.objects.get(id=master_provider_id)
    replica_provs = [core.models.Provider.objects.get(id=replica_id) for replica_id in replica_provider_ids]

    # Iterate through each ApplicationVersion of all applications
    for app in core.models.Application.objects.all():
        for av in app.all_versions:

            av_prov_machines = av.active_machines()

            for prov_machine in av_prov_machines:
                # If ApplicationVersion is available on master provider, replicate it as needed
                if prov_machine.instance_source.provider == master_prov:
                    for replica_prov in replica_provs:
                        # Only replicate if replica provider is missing the ApplicationVersion
                        replica_prov_has_app_version = False
                        # TODO don't reuse variable name
                        for prov_machine in av_prov_machines:
                            if prov_machine.instance_source.provider == replica_prov:
                                replica_prov_has_app_version = True
                        if not replica_prov_has_app_version:
                            if not dry_run:
                                application_to_provider.main(
                                    app.id,
                                    replica_prov.id,
                                    source_provider_id=master_provider_id,
                                    ignore_missing_owner=True,
                                    ignore_missing_members=True
                                )
                            else:
                                dry_run_output.append("Sync application ID {0} to replica provider {1}".format(app.id, replica_prov.id))

    if dry_run:
        pprint.pprint(set(dry_run_output))

def _parse_args():
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("master_provider_id", type=int, help="Master provider ID")
    parser.add_argument("replica_provider_id", type=int, nargs='+', help="Replica provider ID")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes, only print what would be synced")
    return parser.parse_args()

if __name__ == "__main__":
    # Spit log messages to stdout
    output = logging.StreamHandler(sys.stdout)
    output.setLevel(logging.DEBUG)
    output.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(output)
    # Todo should we use a particular logger?
    try:
        args = _parse_args()
        logging.info("Running application_sync_providers with the following arguments:\n{0}".format(str(args)))
        main(args.master_provider_id, args.replica_provider_id, args.dry_run)
    except Exception as e:
        logging.exception(e)
        raise
