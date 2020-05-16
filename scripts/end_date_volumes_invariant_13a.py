#!/usr/bin/env python
import argparse
import django
django.setup()

from core.models import Volume
from django.db import connection
from django.db.models.functions import Now


def main():
    '''
    This script will end date volumes that come up for Invariant #13a on 
    https://tasmo.atmo.cloud and  will be run via cron every ___________.
    '''
    # Dry run option
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not actually end-date any volumes"
    )
    args = parser.parse_args()
    if args.dry_run:
        print 'DRY RUN -- No Volumes will be end-dated'

    volumes_from_invariant_13a = []

    # This query comes from here: https://tasmo.atmo.cloud/queries/64/source#87
    query = '''WITH volumes_users_allocations AS
    ( SELECT volume.id AS volume_id, volume.name AS volume_name, volume.description AS volume_description,
           proj.name AS atmo_project_name, proj.description AS atmo_project_description, au.id AS user_id,
           au.username, au.is_staff, au.is_superuser,
           CASE
               WHEN ins_src.provider_id = 4 THEN 'IU'
               WHEN ins_src.provider_id = 5 THEN 'TACC'
               ELSE 'UNKNOWN'
           END AS src_provider, ins_src.identifier AS openstack_identifier, ins_src.start_date, ins_src.end_date,
           string_agg(current_als.name, ',') AS current_allocation_sources
       FROM volume
       LEFT OUTER JOIN instance_source ins_src ON volume.instance_source_id = ins_src.id
       LEFT OUTER JOIN project proj ON volume.project_id = proj.id
       LEFT OUTER JOIN atmosphere_user au ON ins_src.created_by_id = au.id
       LEFT OUTER JOIN user_allocation_source current_uals ON au.id = current_uals.user_id
       LEFT OUTER JOIN allocation_source current_als ON current_uals.allocation_source_id = current_als.id
       GROUP BY volume.id, proj.id, au.id, ins_src.id), user_allocation_source_deleted_events AS
      ( SELECT DISTINCT event_table.name AS event_name, event_table.entity_id AS username,
                    event_table.payload :: json ->> 'allocation_source_name' AS allocation_source_name,
                    max(TIMESTAMP) AS last_event, min(TIMESTAMP) AS first_event
       FROM event_table
       WHERE event_table.name = 'user_allocation_source_deleted'
       GROUP BY event_table.name, event_table.entity_id, event_table.payload :: json ->> 'allocation_source_name' ),
         user_allocation_source_deleted_events_grouped AS
      ( SELECT DISTINCT event_name, username, string_agg(DISTINCT allocation_source_name, ',') AS historic_allocation_sources,
                    max(last_event) AS last_event, min(first_event) AS first_event
           FROM user_allocation_source_deleted_events
           GROUP BY event_name, username ), users_with_no_allocation_sources AS
      ( SELECT au.id AS user_id, au.username, au.is_staff, au.is_superuser
       FROM atmosphere_user au
       LEFT OUTER JOIN user_allocation_source uas ON au.id = uas.user_id
       WHERE uas.id IS NULL ),
         users_with_no_allocation_source_over_six_months AS
      ( SELECT uwnas.user_id, uwnas.username, uwnas.is_staff, uwnas.is_superuser, uasdeg.last_event, uasdeg.historic_allocation_sources
       FROM users_with_no_allocation_sources uwnas
       LEFT OUTER JOIN user_allocation_source_deleted_events_grouped uasdeg ON uasdeg.username = uwnas.username
       WHERE uasdeg.last_event IS NULL OR uasdeg.last_event < NOW() - INTERVAL '6 months' ),
         active_volumes_for_users_with_no_allocation_source_over_six_months AS
      ( SELECT * FROM volumes_users_allocations vua
       LEFT JOIN users_with_no_allocation_source_over_six_months uwnasosm ON vua.user_id = uwnasosm.user_id
       WHERE uwnasosm.user_id IS NOT NULL AND vua.end_date IS NULL AND vua.username <> 'atmoadmin' ),
       instancesources_appversions_apps AS
      ( SELECT DISTINCT isrc.identifier AS openstack_image_identifier, isrc.start_date AS isrc_start_date,
      isrc.end_date AS isrc_end_date,
        CASE
            WHEN isrc.provider_id = 4 THEN 'IU'
            WHEN isrc.provider_id = 5 THEN 'TACC'
            ELSE 'UNKNOWN'
        END AS isrc_provider, appv.created_by_id AS appv_created_by_id, appv.start_date AS appv_start_date,
            appv.end_date AS appv_end_date, appv.name AS appv_name, app.created_by_id AS app_created_by_id,
            app.name AS app_name, app.description AS app_description, app.start_date AS app_start_date, app.end_date AS app_end_date
       FROM application_version appv
       LEFT OUTER JOIN provider_machine pm ON appv.id = pm.application_version_id
       LEFT OUTER JOIN application app ON app.id = appv.application_id
       LEFT OUTER JOIN instance_source isrc ON pm.instance_source_id = isrc.id ),
         instancesources_appversions_apps_instances AS
      ( SELECT DISTINCT isrc.identifier AS openstack_image_identifier, isrc.start_date AS isrc_start_date,
        isrc.end_date AS isrc_end_date, appv.created_by_id AS appv_created_by_id, appv.start_date AS appv_start_date,
        appv.end_date AS appv_end_date, app.created_by_id AS app_created_by_id, app.start_date AS app_start_date,
        app.end_date AS app_end_date, ins.id AS instance_id, ins.created_by_id AS instance_created_by_id,
        ins.start_date AS instance_start_date, ins.end_date AS instance_end_date
       FROM application_version appv
       LEFT OUTER JOIN provider_machine pm ON appv.id = pm.application_version_id
       LEFT OUTER JOIN application app ON app.id = appv.application_id
       LEFT OUTER JOIN instance_source isrc ON pm.instance_source_id = isrc.id
       LEFT OUTER JOIN instance ins ON isrc.id = ins.source_id ),
         images_users_allocations_agg AS
      ( SELECT DISTINCT isrc.identifier AS openstack_identifier, jsonb_agg(DISTINCT isrc.*) AS instance_sources,
       jsonb_agg(DISTINCT pm.*) AS provider_machine, jsonb_agg(DISTINCT app.*) AS applications,
       jsonb_agg(DISTINCT appv.*) AS application_versions, jsonb_agg(DISTINCT ins.*) AS instances
       FROM application_version appv
       LEFT OUTER JOIN provider_machine pm ON appv.id = pm.application_version_id
       LEFT OUTER JOIN application app ON app.id = appv.application_id
       LEFT OUTER JOIN instance_source isrc ON pm.instance_source_id = isrc.id
       LEFT OUTER JOIN instance ins ON isrc.id = ins.source_id
       GROUP BY isrc.identifier ), active_instancesources_and_appversions_for_users_with_no_allocation_source_over_six_months AS
      ( SELECT iaa.*, uwnasosm.username AS created_by_user_username, uwnasosm.is_staff AS created_by_user_is_staff,
           uwnasosm.is_superuser AS created_by_user_is_superuser, uwnasosm.last_event AS created_by_user_last_allocation_end_date,
           uwnasosm.historic_allocation_sources AS created_by_user_historic_allocation_sources
       FROM instancesources_appversions_apps iaa
       LEFT JOIN users_with_no_allocation_source_over_six_months uwnasosm ON iaa.appv_created_by_id = uwnasosm.user_id
       WHERE uwnasosm.user_id IS NOT NULL AND (isrc_end_date IS NULL OR appv_end_date IS NULL OR app_end_date IS NULL)
         AND uwnasosm.username NOT IN ('admin', 'atmoadmin')), aiaafuwnasosm_with_current_allocation_sources AS
      ( SELECT aiaafuwnasosm.openstack_image_identifier, aiaafuwnasosm.isrc_provider, aiaafuwnasosm.isrc_end_date,
           aiaafuwnasosm.isrc_start_date, aiaafuwnasosm.appv_name, aiaafuwnasosm.appv_start_date, aiaafuwnasosm.appv_end_date,
           aiaafuwnasosm.appv_created_by_id, aiaafuwnasosm.app_end_date, aiaafuwnasosm.app_start_date, aiaafuwnasosm.app_description,
           aiaafuwnasosm.app_name, aiaafuwnasosm.app_created_by_id, aiaafuwnasosm.created_by_user_username,
           aiaafuwnasosm.created_by_user_is_staff, aiaafuwnasosm.created_by_user_is_superuser,
           aiaafuwnasosm.created_by_user_last_allocation_end_date, aiaafuwnasosm.created_by_user_historic_allocation_sources,
           string_agg(DISTINCT current_als.name, ',') AS current_allocation_sources
       FROM active_instancesources_and_appversions_for_users_with_no_allocation_source_over_six_months aiaafuwnasosm
       LEFT OUTER JOIN user_allocation_source current_uals ON aiaafuwnasosm.appv_created_by_id = current_uals.user_id
       LEFT OUTER JOIN allocation_source current_als ON current_uals.allocation_source_id = current_als.id
       GROUP BY aiaafuwnasosm.openstack_image_identifier, aiaafuwnasosm.isrc_provider, aiaafuwnasosm.isrc_end_date,
            aiaafuwnasosm.isrc_start_date, aiaafuwnasosm.appv_name, aiaafuwnasosm.appv_start_date, aiaafuwnasosm.appv_end_date,
            aiaafuwnasosm.appv_created_by_id, aiaafuwnasosm.app_end_date, aiaafuwnasosm.app_start_date,
            aiaafuwnasosm.app_description, aiaafuwnasosm.app_name, aiaafuwnasosm.app_created_by_id,
            aiaafuwnasosm.created_by_user_username, aiaafuwnasosm.created_by_user_is_staff, aiaafuwnasosm.created_by_user_is_superuser,
            aiaafuwnasosm.created_by_user_last_allocation_end_date, aiaafuwnasosm.created_by_user_historic_allocation_sources
       ORDER BY aiaafuwnasosm.created_by_user_last_allocation_end_date ASC )
    SELECT * FROM active_volumes_for_users_with_no_allocation_source_over_six_months avfuwnasosm ORDER BY last_event ASC;'''

    # Use the query above to get volumes listed for Invariant #13a
    with connection.cursor() as cursor:
        cursor.execute(query)

        # Get the results as a dictionary
        rows = dictfetchall(cursor)

        # If there are any results from the query
        if rows:
            volumes = Volume.objects.all()

            # Get the Volume object and put it into our list
            for row in rows:
                volume = volumes.get(pk=row['volume_id'])
                volumes_from_invariant_13a.append(volume)

    print 'Here are volumes from invariant 13a:'
    ctr = 1
    for vol in volumes_from_invariant_13a:
        print ctr
        ctr = ctr + 1
        print vol.name.encode('utf-8')
        print vol
        if not args.dry_run:
            vol.end_date = Now()
            vol.save()
            print 'End-dated %s' % vol
        print '----'

# Helper function to get query results as a dictionary
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


if __name__ == "__main__":
    main()
