#!/usr/bin/env python
import argparse

import django

django.setup()

from core.models import Identity

from service.quota import set_provider_quota


def main():
    """
    Return a list of ALL users on a provider, their CURRENT allocation totals,
    and # of instances used.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Print output rather than perform operation')
    parser.set_defaults(dry_run=False)
    args = parser.parse_args()
    return run_command(args, special_allocation_source='TG-ASC160018')


def run_command(args, special_allocation_source):
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
   HAVING array_agg(allocation_source.name) = '{TG-ASC160018}'
   ORDER BY username) AS users
  LEFT OUTER JOIN public.identity ON identity.created_by_id = users.id
  LEFT OUTER JOIN public.quota ON identity.quota_id = quota.id
WHERE
  identity.quota_id <> 33
  AND identity.quota_id IS NOT NULL;'''

    identities = Identity.objects.raw(raw_query=query)
    for identity in identities:
        print(identity)
        print(identity.quota)
        if not args.dry_run:
            identity.quota_id = 33
            identity.save()
            set_provider_quota(identity.uuid)


if __name__ == "__main__":
    main()
