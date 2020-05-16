#!/usr/bin/env python
import django
django.setup()

from django.conf import settings
from core.models import Provider, Instance, Identity
from service.instance import shelve_instance
from service.cache import get_cached_driver


def main():
    '''
    This script will set active instances that come up for Invariant #12 on 
    https://tasmo.atmo.cloud to 'shelved' status and will be run via cron
    every Tuesday morning.
    '''
    query = '''SELECT
      instance.id,
      instance.name,
      instance.provider_alias,
       CASE
           WHEN instance_source.provider_id = 4
               THEN 'IU'
           WHEN instance_source.provider_id = 5
               THEN 'TACC'
           ELSE 'UNKNOWN' END            AS instance_provider_label,
      instance.start_date,
      instance.end_date,
      last_status.name                  AS last_status,
      last_status.activity              AS last_status_activity,
      last_status.start_date            AS last_status_start_date,
      last_status.end_date              AS last_status_end_date,
      i_als.name                        AS instance_allocation_source,
      au.username,
      au.is_staff,
      au.is_superuser,
      string_agg(current_als.name, ',') AS current_allocation_sources
    FROM instance
      LEFT OUTER JOIN instance_allocation_source_snapshot ialss ON instance.id = ialss.instance_id
      LEFT OUTER JOIN allocation_source i_als ON ialss.allocation_source_id = i_als.id
      LEFT OUTER JOIN atmosphere_user au ON instance.created_by_id = au.id
      LEFT OUTER JOIN user_allocation_source uals
        ON au.id = uals.user_id AND ialss.allocation_source_id = uals.allocation_source_id
      LEFT OUTER JOIN user_allocation_source current_uals on au.id = current_uals.user_id
      LEFT OUTER JOIN allocation_source current_als on current_uals.allocation_source_id = current_als.id
      LEFT OUTER JOIN instance_source ON instance.source_id = instance_source.id
      LEFT JOIN LATERAL
                (
                SELECT
                  ish.start_date,
                  ish.end_date,
                  status.name,
                  ish.activity
                FROM instance_status_history ish
                  LEFT JOIN instance_status status on ish.status_id = status.id
                WHERE ish.instance_id = instance.id
                ORDER BY ish.id DESC
                LIMIT 1
                ) last_status ON TRUE
    WHERE
      instance.end_date IS NULL
      AND last_status.name NOT IN ('shelved_offloaded', 'shelved')
      AND (uals.allocation_source_id IS NULL
           OR ialss.allocation_source_id IS NULL)
    GROUP BY
      instance.id,
      i_als.id,
      instance_source.provider_id,
      au.id,
      last_status.start_date,
      last_status.end_date,
      last_status.name,
      last_status.activity'''

    active_instances_to_shelve = []

    query_instances = Instance.objects.raw(raw_query=query)

    # Getting whitelisted allocation sources
    whitelist = getattr(settings, "ALLOCATION_OVERRIDES_NEVER_ENFORCE")

    # Only want ones that are not by 'atmoadmin'
    for instance in query_instances:
        if instance.created_by.username != 'atmoadmin' and instance.allocation_source.name not in whitelist:
            active_instances_to_shelve.append(instance)

    # Here they are, set them to shelved
    for inst in active_instances_to_shelve:
        reclaim_ip = True

        provider_id = inst.source.provider_id
        provider = Provider.objects.get(pk=provider_id)

        if not provider:
            print 'Provider not found, skipping'  # output to log in service
            continue

        identity = Identity.objects.get(
            created_by__username=inst.username, provider=provider)

        try:
            driver = get_cached_driver(identity=identity)
            esh_instance = driver.get_instance(inst.provider_alias)
            '''if driver:
                print 'got driver'
                print inst.name
                print inst.provider_alias
                print inst.allocation_source.name
                print identity.provider.id
                print identity.id
                print identity.created_by
                print inst.last_status
                print '***'
            else:
                print 'no driver'
            '''

            if inst.last_status == 'active' or inst.last_status == 'shutoff' or inst.last_status == 'deploy_error' or inst.last_status == 'deploying' or inst.last_status == 'suspended':
                shelve_instance(driver, esh_instance, identity.provider.uuid,
                                identity.uuid, identity.created_by, reclaim_ip)
                print "Shelved instance %s (%s) on allocation %s for user %s" % (
                    inst.id, inst.name, inst.allocation_source.name,
                    inst.created_by.username)
            if inst.last_status == 'error':
                raise Exception('Did not shelve instance due to ERROR status')
        except Exception as e:
            print "Could not shelve Instance %s (%s) on allocation %s for user %s - Exception: %s" % (
                inst.id, inst.name, inst.allocation_source.name,
                inst.created_by.username, e)
        continue


if __name__ == "__main__":
    main()
