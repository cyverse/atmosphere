from django.conf import settings
from django.test import TestCase
from dateutil.parser import parse
from datetime import timedelta
from core.models.allocation_source import total_usage
from spoof_instance import UserWorkflow,create_allocation_source
from jetstream.tasks import update_snapshot_cyverse_allocation
from django.utils import timezone

import uuid

class CyverseRulesEngineTest(TestCase):

    def setUp(self):
        if 'cyverse_allocation' not in settings.INSTALLED_APPS:
            self.skipTest('CyVerse Allocation plugin is not enabled')

    def test_total_usage(self):

        ts = parse('2016-10-04T00:00+00:00')
        allocation_source = create_allocation_source(name='TestSource', compute_allowed=1000,timestamp=ts)

        # In this workflow the instance_allocation_source_changed event is fired before any instance status history is created. Hence the instance will report usage as 0.0 because
        # it thinks the allocation source is 'N/A'. A fix for this would be to decouple instance status histories and events completely in the allocation logic.

        workflow1 = UserWorkflow()
        workflow1.assign_allocation_source_to_user(allocation_source, timestamp=ts + timedelta(minutes=10))
        instance = workflow1.create_instance(start_date=ts+timedelta(minutes=30))
        workflow1.create_instance_status_history(instance,start_date=ts+timedelta(days=30),status='suspend')
        workflow1.assign_allocation_source_to_instance(allocation_source, instance,
                                                       timestamp=ts + timedelta(minutes=40))

        report_start_date = ts
        report_end_date=ts + timedelta(minutes=160)

        self.assertEqual(
            total_usage(workflow1.user.username,report_start_date,allocation_source_name=allocation_source.name,end_date=report_end_date),
            2.0)

        workflow2 = UserWorkflow()
        workflow2.assign_allocation_source_to_user(allocation_source, timestamp=ts + timedelta(minutes=10))
        instance = workflow2.create_instance(start_date=ts + timedelta(minutes=30))
        workflow2.assign_allocation_source_to_instance(allocation_source, instance,
                                                       timestamp=ts + timedelta(minutes=40))
        ish_start_date=ts+timedelta(minutes=120)
        workflow2.create_instance_status_history(instance, start_date=ish_start_date,status='suspended')

        report_start_date = ts
        report_end_date = ts+timedelta(minutes=120)

        self.assertEqual(
            total_usage(workflow2.user.username, report_start_date, allocation_source_name=allocation_source.name,
                        end_date=report_end_date),
            1.33)

        # check total allocation usage so far
        end_date = ts+timedelta(days=30)
        update_snapshot_cyverse_allocation(ts,end_date)
        self.assertEqual( float(allocation_source.compute_used) , 720.66 )



