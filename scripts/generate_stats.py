#!/usr/bin/env python
import requests
from django.utils import timezone
from datetime import timedelta, datetime
import django
django.setup()


def main():
    now = timezone.now()
    print "ONE YEAR AGO:"
    print ""
    year_ago = now - timezone.timedelta(days=365)
    get_statistics(year_ago)
    print "THIS MONTH:"
    print ""
    this_month = now - timezone.timedelta(days=now.day - 1)
    get_statistics(this_month)


def get_statistics(past_time):
    now = timezone.now()
    print "Checking statistics from %s to %s" % (past_time.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'))
    resp = requests.get(
        "http://wesley.iplantc.org/api/leaderboard?from=%s&until=%s"
        % (past_time.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')))
    json_data = resp.json()
    print_statistics(json_data)


def print_statistics(json_data):
    count = 20
    # Gather Stats
    by_count = most_launched(json_data, count)
    by_time = most_time(json_data, count)
    by_uptime = most_uptime(json_data, count)
    stats = total_launched(json_data)

    # Pretty Print
    print "Top %s users - (Launched the most instances)" % count
    for obj in by_count:
        print '%s - %s' % (obj['username'], obj['instance_count'])
    print '---'

    print "Top %s users - (Most CPU time used)" % count
    for obj in by_time:
        print '%s - %s' % (obj['username'], print_time(obj['total_cpu_time']))
    print '---'

    print "Top %s users - (Most Uptime)" % count
    for obj in by_uptime:
        print '%s - %s' % (obj['username'], print_time(obj['total_uptime']))
    print '---'

    print "Cumulative Statistics:"
    print "Total CPU Time: %s\nTotal running time: %s\n Total Instances launched: %s"\
        % (print_time(stats['total_cpu_time']), print_time(stats['total_uptime']), stats['total_count'])


def print_time(seconds):
    # NOTE: Must figure out the unit of time
    # OPT 1:
    hours = seconds // 3600
    return "%s hours" % hours
    # OPT 2:


def most_launched(json_data, count=20):
    sorted_json = sort_and_filter(
        json_data,
        sort_key=lambda obj: obj['instance_count'])
    return sorted_json[:count]


def most_uptime(json_data, count=20):
    sorted_json = sort_and_filter(
        json_data,
        sort_key=lambda obj: obj['total_uptime'])
    return sorted_json[:count]


def most_time(json_data, count=20):
    sorted_json = sort_and_filter(
        json_data,
        sort_key=lambda obj: obj['total_cpu_time'])
    return sorted_json[:count]


def sort_and_filter(json_data, sort_key, filter_key=None, no_staff=True):
    sorted_json = sorted(json_data, key=sort_key, reverse=True)

    if filter_key:
        filtered_json = filter(filter_key, sorted_json)
    else:
        filtered_json = sorted_json

    if no_staff:
        filtered_json = filter(lambda obj: not obj['is_staff'], filtered_json)

    return filtered_json


def prettydate(d):
    diff = datetime.datetime.utcnow() - d
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{} days ago'.format(diff.days)
    elif s <= 1:
        return 'just now'
    elif s < 60:
        return '{} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{} minutes ago'.format(s / 60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{} hours ago'.format(s / 3600)


def total_launched(json_data):
    total_cpu_time = 0
    total_uptime = 0
    total_count = 0
    for obj in json_data:
        total_cpu_time += obj['total_cpu_time'] if obj['total_cpu_time'] else 0
        total_uptime += obj['total_uptime'] if obj['total_uptime'] else 0
        total_count += int(obj['instance_count'])
    return {
        'total_cpu_time': total_cpu_time,
        'total_uptime': total_uptime,
        'total_count': total_count}

if __name__ == "__main__":
    main()
