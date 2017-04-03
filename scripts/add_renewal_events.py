import sys
import uuid

import os

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
os.environ["DJANGO_SETTINGS_MODULE"] = "atmosphere.settings"

import django

django.setup()
from jetstream.models import TASAPIDriver
from core.models import EventTableUpdated

# fetch values from TACC
api = TASAPIDriver()
allocations = api.get_all_projects()

for source in allocations:
    for details in source['allocations']:

        hashstring = '%s_%s' % (source['chargeCode'], details['id'])
        hashed_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(hashstring))

        payload = {
            "start_date": details['start'],
            "end_date": details['end'],
            "compute_allocated": details['computeAllocated'],
            "allocation_source_name": source['chargeCode'],
        }

        try:

            e = EventTableUpdated(
                uuid=hashed_uuid,
                name="allocation_source_created_or_renewed",
                payload=payload,
                entity_id=payload['allocation_source_name'],
                timestamp=payload['start_date'])
            e.save()
        except:
            continue
