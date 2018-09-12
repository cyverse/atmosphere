from django.core.management import call_command
from django.test import TestCase
import datetime
import pytz

from core.management.commands import maintenance
from core.models import MaintenanceRecord

class MaintenanceTest(TestCase):
    def test_start(self):
        records_before = set(MaintenanceRecord.objects.all())
        call_command(
            maintenance.Command(),
            "start",
            title="title",
            message="message",
            start_date="2038-01-19T03:15:00Z")
        records_after = set(MaintenanceRecord.objects.all())

        created_records = records_after - records_before
        self.assertEqual(len(created_records), 1, "One record was created")

        record = next(iter(created_records))
        self.assertEqual(record.title, "title")
        self.assertEqual(record.message, "message")
        self.assertEqual(record.start_date,
            datetime.datetime(2038, 1, 19, 3, 15, tzinfo=pytz.utc))
        self.assertIsNone(record.end_date)

    def test_start_dry_run(self):
        """
        The start command with --dry-run shouldn't create a record
        """
        num_records_before = MaintenanceRecord.objects.count()
        call_command(maintenance.Command(), "start", "--dry-run")
        num_records_after = MaintenanceRecord.objects.count()
        self.assertEqual(
            num_records_before, num_records_after,
            "The number of records before and after shouldn't change")

    def test_stop(self):
        records_before = set(MaintenanceRecord.objects.all())
        call_command(maintenance.Command(), "start")
        records_after = set(MaintenanceRecord.objects.all())
        created_record = next(iter(records_after - records_before))

        call_command(maintenance.Command(), "stop")
        updated_record = MaintenanceRecord.objects.get(id=created_record.id)
        self.assertIsNotNone(updated_record.end_date, "Record has an enddate")
