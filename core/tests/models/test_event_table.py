import uuid

from django.core import exceptions
from django.test import TestCase, override_settings

from api.tests.factories import UserFactory
from core.models import EventTable, AllocationSource
from core.models import UserAllocationSource


class AllocationSourceSnapshotEventTest(TestCase):
    def setUp(self):
        user = UserFactory.create()
        self.user = user
        self.allocation_source_id = str(uuid.uuid4())
        self.alloc_src = AllocationSource.objects.create(name='DefaultAllocation', source_id=self.allocation_source_id,
                                                         compute_allowed=1000)
        UserAllocationSource.objects.create(user=user, allocation_source=self.alloc_src)


class AllocationSourceSnapshotEventTestBasicCreate(AllocationSourceSnapshotEventTest):
    @override_settings(ALLOCATION_SOURCE_WARNINGS=[10, 25, 50, 75, 90])
    def test_basic_create_event(self):
        initial_event_count = EventTable.objects.count()

        event_payload = {
            'allocation_source_id': self.alloc_src.source_id,
            'compute_used': 100.00,  # 100 hours used ( a number, not a string!)
            'global_burn_rate': 2.00,  # 2 hours used each hour
        }
        print(event_payload)
        EventTable.create_event(name='allocation_source_snapshot', payload=event_payload,
                                entity_id=self.alloc_src.source_id)
        subsequent_event_count = EventTable.objects.count()
        # self.assertEqual(subsequent_event_count - initial_event_count, 2)
        # TODO: Figure out why it's not creating the `allocation_source_threshold_met` event.
        self.assertEqual(subsequent_event_count - initial_event_count, 2)

        threshold_met_event = EventTable.objects.filter(entity_id=self.alloc_src.source_id,
                                                        name='allocation_source_threshold_met').last()

        self.assertEqual(threshold_met_event.name, 'allocation_source_threshold_met')
        self.assertEqual(threshold_met_event.entity_id, self.alloc_src.source_id)
        self.assertEqual(threshold_met_event.payload, {'actual_value': 10,
                                                       'allocation_source_id': self.alloc_src.source_id,
                                                       'threshold': 10})


class AllocationSourceSnapshotEventTestValidEvents(AllocationSourceSnapshotEventTest):
    def test_valid_events(self):
        initial_event_count = EventTable.objects.count()

        valid_events = (
            {
                'description': 'Basic sanity test',
                'entity_id': self.alloc_src.source_id,
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
                'entity_id': self.alloc_src.source_id,
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
            },
            {
                'description': 'String instead of float - String should be converted to float',
                'entity_id': self.alloc_src.source_id,
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': '10.00',  # Case: String instead of float
                        'global_burn_rate': 2.00
                    },
                'expected_serialized_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': 10.00,
                        'global_burn_rate': 2.00
                    }
            },
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

        subsequent_event_count = EventTable.objects.count()
        self.assertEqual(subsequent_event_count - initial_event_count, len(valid_events))


class AllocationSourceSnapshotEventTestInvalidEvents(AllocationSourceSnapshotEventTest):
    def test_fail_schema(self):
        """Ensure event creation fails if it does not match schema"""

        initial_event_count = EventTable.objects.count()
        some_random_uuid = str(uuid.uuid4())

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
            {
                'description': 'TODO: Unknown Allocation Source',
                'skip': True,
                'entity_id': some_random_uuid,
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': some_random_uuid,
                        'compute_used': '10.00',
                        'global_burn_rate': 2.00,
                    }
            },
            {
                'description': 'TODO: The entity_id and allocation_source_id do not match',
                'skip': True,
                'entity_id': self.alloc_src.source_id,
                'name': 'allocation_source_snapshot',
                'raw_payload':
                    {
                        'allocation_source_id': self.alloc_src.source_id,
                        'compute_used': '10.00',
                        'global_burn_rate': 2.00,
                    }
            },
        )

        missing_error_cases = []
        for event_data in invalid_events:
            if event_data.get('skip') is True:
                continue
            raw_payload = event_data['raw_payload']
            print('Testing: {}'.format(event_data['description']))
            try:
                EventTable.create_event(name='allocation_source_snapshot', payload=raw_payload,
                                        entity_id=self.alloc_src.source_id)
            except exceptions.ValidationError as validation_error:
                self.assertEqual(validation_error.code, 'event_schema')
                self.assertEqual(validation_error.message, 'Does not comply with event schema')
            else:
                missing_error_cases.append(event_data['description'])

        # Skip cases which we have not finished implementing yet
        subsequent_event_count = EventTable.objects.count()
        self.assertEqual(subsequent_event_count - initial_event_count, 0)

    def test_fail_unknown_event(self):
        """Ensure event creation fails if it does not match known events"""

        initial_event_count = EventTable.objects.count()

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

        subsequent_event_count = EventTable.objects.count()
        self.assertEqual(subsequent_event_count - initial_event_count, 0)
