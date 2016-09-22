from django.test import TestCase, override_settings

from api.tests.factories import UserFactory
from core.models import EventTable, AllocationSource
from core.models import UserAllocationSource


class EventTableTest(TestCase):
    def setUp(self):
        pass

    @override_settings(ALLOCATION_SOURCE_WARNINGS=[10, 25, 50, 75, 90])
    def test_create_event(self):
        event_count = EventTable.objects.count()
        self.assertEqual(event_count, 0)
        user = UserFactory.create()
        alloc_src = AllocationSource.objects.create(name='DefaultAllocation', source_id='37623',
                                                    compute_allowed=1000)
        UserAllocationSource.objects.create(user=user, allocation_source=alloc_src)
        event_payload = {
            'allocation_source_id': alloc_src.source_id,
            'compute_used': 100.00,  # 100 hours used ( a number, not a string!)
            'global_burn_rate': 2.00,  # 2 hours used each hour
        }
        new_event = EventTable.create_event(name='allocation_source_snapshot', payload=event_payload,
                                            entity_id=alloc_src.source_id)
        event_count = EventTable.objects.count()
        self.assertEqual(event_count, 2)
        events = EventTable.objects.all()
        self.assertEqual(new_event, events[1])
        self.assertEqual(events[0].name, 'allocation_source_threshold_met')
        self.assertEqual(events[0].entity_id, alloc_src.source_id)
        self.assertEqual(events[0].payload, {'actual_value': 10,
                                             'allocation_source_id': alloc_src.source_id,
                                             'threshold': 10})
