#!/usr/bin/env python
"""
This script serves a very specific purpose:
    Nullifying all non-end-dated status history objects that are not the latest value.
"""

from core.models import Provider, Instance, InstanceStatusHistory
import django
django.setup()
provs = Provider.get_active()
for instance in Instance.objects.filter(
        source__provider__in=provs).order_by('created_by'):
    prev_history = None
    try:
        last_history = instance.instancestatushistory_set.latest('pk')
    except InstanceStatusHistory.DoesNotExist:
        continue
    for history in instance.instancestatushistory_set.order_by('start_date'):
        if not history.end_date and history.id != last_history.id:
            print "Provider: %s" % instance.source.provider.location
            print "Owner: %s" % instance.created_by.username
            print "Instance: %s Bad History: %s" % (instance.provider_alias, history)
            history.end_date = history.start_date
            history.save()
    prev_history = None
    for history in instance.instancestatushistory_set.order_by('start_date'):
        if prev_history and prev_history.status.name == history.status.name\
                and history.end_date != history.start_date:
            print "Provider: %s" % instance.source.provider.location
            print "Owner: %s" % instance.created_by.username
            print "Instance: %s Duplicate History with status %s" %\
                (instance.provider_alias, history)
            history.end_date = history.start_date
            history.save()
        prev_history = history
