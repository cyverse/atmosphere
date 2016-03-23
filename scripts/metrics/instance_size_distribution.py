#!/usr/bin/env python

from collections import OrderedDict
import argparse
import subprocess
import logging

import django
django.setup()

from dateutil.parser import parse

from django.db.models import Q
from django.utils.timezone import datetime, timedelta, now
from core.models import Instance, Size, Provider


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=int,
                        help="Atmosphere provider ID to use.")
    parser.add_argument("--date", default=None,
                        help="Date to start counting backwards (Default: Now)")
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="# Days to count backwards from time (Default:365)")
    args = parser.parse_args()
    # Parse
    if not args.provider:
        raise Exception("Required argument 'provider' is missing. Please provide the DB ID of the provider to continue.")
    else:
        provider = Provider.objects.get(id=args.provider)
    is_now = True
    try:
        date_value = parse(args.date)
        if not date_value:
            date_value = now()
        else:
            is_now = False
    except Exception:
        date_value = now()
    size_distribution = instance_size_distribution(
        provider.id,
        args.days,
        date_value)
    print size_distribution


def _instantiate_size_distribution(provider_id):
    size_distribution = OrderedDict()
    for size in Size.objects.filter(
            provider__id=provider_id).order_by(
            'cpu', 'mem', 'id'):
        size_distribution[size.name] = 0
    return size_distribution


def instance_size_distribution(provider_id, days_ago, now_time, is_now=True):
    size_distribution = _instantiate_size_distribution(provider_id)
    DATE = now_time - timedelta(days=days_ago)
    if is_now:
        instances = Instance.objects.filter(
            Q(end_date__gt=DATE) | Q(end_date__isnull=True),
            source__provider__id=provider_id)
    else:
        instances = Instance.objects.filter(
            Q(end_date__gt=DATE),
            source__provider__id=provider_id)
    for instance in instances:
        unique_sizes = instance.instancestatushistory_set.values_list(
            'size',
            flat=True).distinct()
        for size_id in unique_sizes:
            size = Size.objects.get(id=size_id)
            count = size_distribution.get(size.name, 0)
            count += 1
            size_distribution[size.name] = count
    return size_distribution

if __name__ == "__main__":
    main()
