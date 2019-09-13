#!/usr/bin/env python
import argparse

import django

django.setup()

from core.models import Identity, Quota

from service.quota import set_provider_quota, _get_hard_limits


def main():
    """
    Reset quotas for users on a particular allocation source
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Print output rather than perform operation')
    parser.add_argument('--allocation-source', required=True,
                        help='Allocation source name to reset quotas for, e.g. TG-ASC160018')
    parser.add_argument('--quota-id', required=True, type=int,
                        help='Quota ID to set')
    parser.add_argument('--whitelist-quota-ids', type=lambda s: [int(item.strip()) for item in s.split(',')],
                        help='Quota IDs that are acceptable and won\'t be overwritten (comma separated)')
    parser.set_defaults(dry_run=False)
    args = parser.parse_args()
    return run_command(args.dry_run,
                       args.allocation_source,
                       args.quota_id,
                       args.whitelist_quota_ids)


def run_command(dry_run, allocation_source, quota_id, whitelist_quota_ids):
    query = '''SELECT identity.*
FROM
  (SELECT
     atmosphere_user.id,
     atmosphere_user.username,
     array_agg(allocation_source.name) allocation_sources
   FROM public.atmosphere_user
     LEFT JOIN public.user_allocation_source ON atmosphere_user.id = user_allocation_source.user_id
     LEFT JOIN public.allocation_source ON user_allocation_source.allocation_source_id = allocation_source.id
   GROUP BY atmosphere_user.id
   HAVING array_agg(allocation_source.name) = %(allocation_source)s
   ORDER BY username) AS users
  LEFT OUTER JOIN public.identity ON identity.created_by_id = users.id
  LEFT OUTER JOIN public.quota ON identity.quota_id = quota.id
WHERE
  identity.quota_id NOT IN %(acceptable_quota_ids)s 
  AND identity.quota_id IS NOT NULL;'''

    params = {
        'allocation_source': '{%s}' % allocation_source,
        'acceptable_quota_ids': tuple(whitelist_quota_ids + [quota_id])
    }
    identities = Identity.objects.raw(raw_query=query, params=params)
    # print('Query to find identities:')
    # print(identities.query)

    quota_to_set = Quota.objects.get(id=quota_id)
    # print('\nDesignated quota: {}'.format(quota_to_set))

    for identity in identities:
        print('\n========================\n')
        print('Identity: {}'.format(identity))
        print('Current quota in DB: {}'.format(identity.quota))
        current_provider_quota = _get_hard_limits(identity)
        print('Current quota in provider: {}'.format(current_provider_quota))
        if dry_run:
            print('DRY-RUN: Not changing quota to {}'.format(quota_id))
        else:
            print('Changing provider quota to {}...'.format(quota_id))
            updated_provider_quota = set_provider_quota(identity.uuid, quota=quota_to_set)
            print('Updated provider quota: {}'.format(updated_provider_quota))
            print('Changing DB quota to {}...'.format(quota_id))
            identity.quota = quota_to_set
            identity.save()
            print('Updated DB quota: {}'.format(identity.quota_id))


if __name__ == "__main__":
    main()
