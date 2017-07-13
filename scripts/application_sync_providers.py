#!/usr/bin/env python

import argparse
import json
import logging
import sys
import pprint

import application_to_provider
import django; django.setup()
import core.models

description = """
This script performs a one-way synchronization of Applications (a.k.a. images)
from a master Provider to one or more replica Providers. Only synchronizes
non-end-dated Applications and ApplicationVersions.

If --irods-conn and --irods-collections are defined, then iRODS transfer mode
will be used for each provider ID defined in the --irods-collections JSON.
Pure Glance API will be used to transfer image data for any providers not
defined in --irods-collections. When using iRODS Transfer, the same
requirements and caveats apply as detailed in application_to_provider.py.
"""


def _parse_args():
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("master_provider_id", type=int, help="Master provider ID")
    parser.add_argument("replica_provider_id", type=int, nargs='+', help="Replica provider ID")
    parser.add_argument("--irods-conn", type=str, metavar="irods://user:password@host:port/zone",
                        help="iRODS connection string in the form of irods://user:password@host:port/zone")
    # https://stackoverflow.com/questions/18608812/accepting-a-dictionary-as-an-argument-with-argparse-and-python
    parser.add_argument("--irods-collections", type=json.loads,
                        metavar="'{\"1\": \"/myzone/foo\", \"2\": \"/myzone/bar\"}'",
                        help="JSON associating mapping each provider ID to an iRODS collection containing images, e.g. "
                        "'{\"1\": \"/myzone/foo\", \"2\": \"/myzone/bar\"}'")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes, only print what would be synced")
    return parser.parse_args()


def main(master_provider_id, replica_provider_ids, dry_run=False, irods_conn=None, irods_collections=None):

    # Convert provider IDs from unicode objects to integers
    # https://stackoverflow.com/questions/21193682/convert-a-string-key-to-int-in-a-dictionary
    if irods_collections:
        irods_collections = {int(k): v for k, v in irods_collections.items()}

    # Sanity checking
    if any([irods_conn, irods_collections]):
        if all([irods_conn, irods_collections]):
            for key in irods_collections.keys():
                irods_path = irods_collections[key]
                assert(type(irods_path) == unicode and len(irods_path) > 1 and irods_path[0] == "/")
            assert(master_provider_id in irods_collections.keys())
        else:
            raise Exception("If using iRODS transfer then irods_conn and irods_collections must be defined")

    for id in replica_provider_ids:
        if id == master_provider_id:
            raise Exception("Master provider cannot also be a replica")
    if len(replica_provider_ids) > len(set(replica_provider_ids)):
        raise Exception("No duplicate replica providers allowed")

    if dry_run:
        dry_run_output = []

    # Resolve providers
    master_prov = core.models.Provider.objects.get(id=master_provider_id)
    replica_provs = [core.models.Provider.objects.get(id=replica_id) for replica_id in replica_provider_ids]

    # Iterate through each ApplicationVersion of all applications
    for app in core.models.Application.objects.filter(end_date__isnull=True):
        logging.debug("Processing application {0}".format(app))
        replicate_app = False
        for av in app.active_versions():
            for pm in av.active_machines():
                # If ApplicationVersion is available on master provider, replicate it as needed
                if pm.instance_source.provider == master_prov:
                    replicate_app = True

        if replicate_app:
            logging.debug("Replicating application {0} as needed".format(app))
            for replica_prov in replica_provs:
                if not _app_complete_on_provider(app, replica_prov):
                    logging.info("Migrating application {0} to provider {1}".format(app, replica_prov))
                    if not dry_run:
                        if irods_collections and replica_prov.id in irods_collections.keys():
                            application_to_provider.main(
                                app.id,
                                replica_prov.id,
                                source_provider_id=master_prov.id,
                                ignore_missing_owner=True,
                                ignore_missing_members=True,
                                irods_conn_str=irods_conn,
                                irods_src_coll=irods_collections[master_prov.id],
                                irods_dst_coll=irods_collections[replica_prov.id]
                            )
                        else:
                            application_to_provider.main(
                                app.id,
                                replica_prov.id,
                                source_provider_id=master_provider_id,
                                ignore_missing_owner=True,
                                ignore_missing_members=True
                            )
                        logging.info("Migrated application {0} to provider {1}".format(app, replica_prov))
                    else:
                        # Dry run
                        if irods_collections and (replica_prov.id in irods_collections.keys()):
                            dry_run_output.append(
                                "Sync application ID {0} to replica provider {1} using iRODS transfer -- "
                                "source collection: {2} destination collection: {3}".format(
                                    app.id,
                                    replica_prov.id,
                                    irods_collections[master_prov.id],
                                    irods_collections[replica_prov.id]
                                    ))
                        else:
                            dry_run_output.append(
                                "Sync application ID {0} to replica provider {1}".format(app.id,
                                                                                         replica_prov.id))

    if dry_run:
        pprint.pprint(set(dry_run_output))


def _app_complete_on_provider(application, provider):
    """
    Determines if an Application is completely available on a Provider, i.e. all active ApplicationVersions have a
    ProviderMachine + InstanceSource on given Provider.

    Args:
        application: Application object
        provider: Provider object

    Returns: boolean
    """
    for av in application.active_versions():
        av_on_prov = False
        for prov_machine in av.active_machines():
            if prov_machine.instance_source.provider == provider:
                av_on_prov = True
        if not av_on_prov:
            return False
    return True


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
        main(args.master_provider_id,
             args.replica_provider_id,
             args.dry_run,
             args.irods_conn,
             args.irods_collections)
    except Exception as e:
        logging.exception(e)
        raise
