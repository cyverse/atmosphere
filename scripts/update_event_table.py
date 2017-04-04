import sys,os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
os.environ["DJANGO_SETTINGS_MODULE"] = "atmosphere.settings"

import django; django.setup()
from django.db.models.query import Q
from core.models import EventTable, EventTableUpdated, AllocationSource
from django.db.models.signals import post_save
from core.hooks.allocation_source import (
    listen_for_allocation_threshold_met,
    listen_for_instance_allocation_changes,
    listen_for_allocation_source_created_or_renewed,
    listen_for_allocation_source_compute_allowed_changed
)


def toggle_signals(on=True):
    if on:
        post_save.connect(listen_for_allocation_threshold_met, sender=EventTable)
        post_save.connect(listen_for_instance_allocation_changes, sender=EventTable)
        post_save.connect(listen_for_allocation_source_created_or_renewed,sender=EventTable)
        post_save.connect(listen_for_allocation_source_compute_allowed_changed,sender=EventTable)

    else:
        post_save.disconnect(listen_for_allocation_threshold_met, sender=EventTable)
        post_save.disconnect(listen_for_instance_allocation_changes, sender=EventTable)
        post_save.disconnect(listen_for_allocation_source_created_or_renewed, sender=EventTable)
        post_save.disconnect(listen_for_allocation_source_compute_allowed_changed, sender=EventTable)

if __name__=='__main__':
    toggle_signals(on=False)

    all_events = EventTable.objects.filter(
        Q(name="instance_allocation_source_changed") | Q(name="allocation_source_threshold_met"))

    #Fill EventTableUpdated with these events
    toggle_signals(on=False)
    for event in all_events:
        source_name = AllocationSource.objects.get(source_id=event.payload['allocation_source_id']).name

        if event.name=="allocation_source_threshold_met":
            entity_id =source_name
            new_payload = {"allocation_source_name":source_name,"threshold":event.payload["threshold"],"actual_value":event.payload["actual_value"]}
        else:
            entity_id = event.entity_id
            new_payload = {"allocation_source_name": source_name, "instance_id": event.payload["instance_id"]}
            # take care of very old events with incorrect payloads..otherwise calculations will be incorrect
            if len(event.payload.keys()) > 2:
                new_payload['username'] = event.payload["username"]


        event.payload = new_payload
        event.entity_id = entity_id

        event.save()

    toggle_signals()