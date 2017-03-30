import sys,os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
os.environ["DJANGO_SETTINGS_MODULE"] = "atmosphere.settings"

import django; django.setup()
from jetstream.models import TASAPIDriver
from django.db.models import Count
from core.models import EventTableUpdated, AllocationSource


# fetch values from TACC
api = TASAPIDriver()
allocations = api.get_all_projects()

# Find duplicate allocation source names

dupes = AllocationSource.objects.values('name').annotate(Count('id')).order_by().filter(id__count__gt=1)

duplicate_values = AllocationSource.objects.filter(name__in=[item['name'] for item in dupes]).distinct('name').values_list('name', flat=True)

for source in allocations:
    if source['chargeCode'] in duplicate_values:
        details = source['allocations'][-1]
        payload = {
            "start_date" : details['start'],
            "compute_allocated" : details['computeAllocated'],
            "allocation_source_name" : source['chargeCode'],
        }

        e = EventTableUpdated(
                name="allocation_source_renewed",
                payload=payload,
                entity_id=payload['allocation_source_name'],
                timestamp=payload['start_date'])

        e.save()

