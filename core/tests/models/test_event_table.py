from django.core import exceptions
from django.test import TestCase, override_settings

from api.tests.factories import UserFactory
from core.models import EventTable, AllocationSource
from core.models import UserAllocationSource


class AllocationSourceSnapshotEventTest(TestCase):
    def setUp(self):
        user = UserFactory.create()
        self.user = user
        self.alloc_src = AllocationSource.objects.create(name='DefaultAllocation', source_id='37623',
                                                         compute_allowed=1000)
        UserAllocationSource.objects.create(user=user, allocation_source=self.alloc_src)

    @override_settings(ALLOCATION_SOURCE_WARNINGS=[10, 25, 50, 75, 90])
    def test_basic_create_event(self):
        event_count = EventTable.objects.count()
        self.assertEqual(event_count, 0)

        event_payload = {
            'allocation_source_id': self.alloc_src.source_id,
            'compute_used': 100.00,  # 100 hours used ( a number, not a string!)
            'global_burn_rate': 2.00,  # 2 hours used each hour
        }
        print(event_payload)
        new_event = EventTable.create_event(name='allocation_source_snapshot', payload=event_payload,
                                            entity_id=self.alloc_src.source_id)
        event_count = EventTable.objects.count()
        self.assertEqual(event_count, 2)
        events = EventTable.objects.all()
        self.assertEqual(new_event, events[1])
        self.assertEqual(events[0].name, 'allocation_source_threshold_met')
        self.assertEqual(events[0].entity_id, self.alloc_src.source_id)
        self.assertEqual(events[0].payload, {'actual_value': 10,
                                             'allocation_source_id': self.alloc_src.source_id,
                                             'threshold': 10})

    def test_valid_events(self):
        event_count = EventTable.objects.count()
        self.assertEqual(event_count, 0)

        valid_events = (
            {
                'description': 'Basic sanity test',
                'entity_id': 'some_entity_id',
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': 10.00,
                        'global_burn_rate': 2.00
                    }
            },
            {
                'description': 'Extra field should be stripped out by serializer',
                'entity_id': 'some_entity_id',
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': 10.00,
                        'global_burn_rate': 2.00,
                        'extra_field': 'some_value'
                    },
                'expected_serialized_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': 10.00,
                        'global_burn_rate': 2.00
                    }
            }
        )
        for event_data in valid_events:
            raw_payload = event_data['raw_payload']
            print('Testing: {}'.format(event_data['description']))
            new_event = EventTable.create_event(name=event_data['name'], payload=raw_payload,
                                                entity_id=event_data['entity_id'])
            self.assertEqual(new_event.name, event_data['name'])
            self.assertEqual(new_event.entity_id, event_data['entity_id'])
            expected_serialized_payload = event_data.get('expected_serialized_payload') or raw_payload
            self.assertEqual(new_event.payload, expected_serialized_payload)

        event_count = EventTable.objects.count()
        self.assertEqual(event_count, len(valid_events))

    def test_fail_schema(self):
        """Ensure event creation fails if it does not match schema"""

        # noinspection SpellCheckingInspection
        invalid_events = (
            {
                'description': 'Typo in field name',
                'entity_id': self.alloc_src.source_id,
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_souce_id': self.alloc_src.source_id,  # Case: Typo in field name
                        'compute_used': 10.00,
                        'global_burn_rate': 2.00,
                    }
            },
            {
                'description': 'Number instead of string ID',
                'entity_id': self.alloc_src.source_id,
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': 37623,  # Case: Number instead of string ID
                        'compute_used': 10.00,
                        'global_burn_rate': 2.00
                    }
            },
            {
                'description': 'String instead of float',
                'entity_id': self.alloc_src.source_id,
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': '10.00',  # Case: String instead of float
                        'global_burn_rate': 2.00
                    }
            },
            {
                'description': 'Missing field',
                'entity_id': self.alloc_src.source_id,
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': '10.00',
                        # Case: Missing field
                    }
            },
        )

        for event_data in invalid_events:
            raw_payload = event_data['raw_payload']
            print('Testing: {}'.format(event_data['description']))
            with self.assertRaises(exceptions.ValidationError) as validation_error:
                EventTable.create_event(name='allocation_source_snapshot', payload=raw_payload,
                                        entity_id=self.alloc_src.source_id)
            self.assertEqual(validation_error.exception.code, 'event_schema')
            self.assertEqual(validation_error.exception.message, 'Does not comply with event schema')

            event_count = EventTable.objects.count()
            self.assertEqual(event_count, 0)

    def test_fail_unknown_event(self):
        """Ensure event creation fails if it does not match known events"""
        event_payload = {
            'allocation_source_id': self.alloc_src.source_id,  # Typo in field name
            'compute_used': 10.00,
            'global_burn_rate': 2.00
        }
        # noinspection SpellCheckingInspection
        invalid_event_name = 'allocation_souce_snapshot'  # Test for typo
        with self.assertRaises(exceptions.ValidationError) as validation_error:
            EventTable.create_event(name=invalid_event_name, payload=event_payload,
                                    entity_id=self.alloc_src.source_id)
        self.assertEqual(validation_error.exception.code, 'event_schema')
        # noinspection SpellCheckingInspection
        self.assertEqual(validation_error.exception.message, 'Unrecognized event name: allocation_souce_snapshot')

        event_count = EventTable.objects.count()
        self.assertEqual(event_count, 0)
