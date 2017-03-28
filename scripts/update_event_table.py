import sys,os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
os.environ["DJANGO_SETTINGS_MODULE"] = "atmosphere.settings"

import django; django.setup()
from django.db.models.query import Q
from core.models import EventTable, EventTableUpdated, AllocationSource

all_events = EventTable.objects.filter(
    Q(name="instance_allocation_source_changed") | Q(name="allocation_source_threshold_met"))

#Fill EventTableUpdated with these events

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


    e = EventTableUpdated(
        name=event.name, payload=new_payload, entity_id=entity_id, timestamp=event.timestamp, uuid=event.uuid)

    e.save()