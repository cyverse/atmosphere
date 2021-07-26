#!/usr/bin/env python
"""
Switch user to a different quota on a given provider

e.g.
python switch_user_quota.py --provider 123 --username foobar --quota 10
"""

import argparse

import django

django.setup()

from core.models import AtmosphereUser as User
from core.models import Provider, Identity, Quota


def main():
    args = parse_args()

    user, quota, provider = lookup_n_validate(
        args.username, args.quota, args.provider
    )
    iden = lookup_identity(user, provider)

    print(
        "Identity(before) {}, {}, {}, {}".format(
            iden.uuid, iden.created_by.username, iden.provider.location,
            iden.quota.id
        )
    )

    if not args.dry_run:
        iden.quota = quota
        iden.save()
        print("Quota switch to {}".format(quota.id))

    print(
        "Identity(after) {}, {}, {}, {}".format(
            iden.uuid, iden.created_by.username, iden.provider.location,
            iden.quota.id
        )
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", type=int, required=True, help="Atmosphere provider ID"
    )
    parser.add_argument(
        "--username", type=str, required=True, help="Username of the user"
    )
    parser.add_argument(
        "--quota", type=int, required=True, help="Quota ID to switch to"
    )
    parser.add_argument(
        "--dry-run", action='store_true', help="Quota ID to switch to"
    )
    args = parser.parse_args()
    return args


def lookup_user(username):
    user = User.objects.get(username=username)
    return user


def lookup_quota(quota_id):
    quota = Quota.objects.get(id=quota_id)
    return quota


def lookup_provider(provider_id):
    provider = Provider.objects.get(id=provider_id)
    return provider


def lookup_n_validate(username, quota_id, provider_id):
    try:
        user = lookup_user(username)
        quota = lookup_quota(quota_id)
        provider = lookup_provider(provider_id)
    except Exception as exc:
        raise exc
    return user, quota, provider


def lookup_identity(user, provider):
    try:
        iden = Identity.objects.get(created_by=user, provider=provider)
        if not iden:
            print("Identity not found")
            exit(1)
    except Exception as exc:
        print("Identity not found, {}, {}".format(user, provider))
        raise exc
    return iden


if __name__ == "__main__":
    main()
