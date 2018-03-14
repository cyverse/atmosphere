import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from dateutil.parser import parse

from core.models import MaintenanceRecord
from atmosphere.version import git_branch


class Command(BaseCommand):
    help = 'Allows starting and stopping maintenance'

    def add_arguments(self, parser):
        default_title = _default_title()
        default_message = _default_message()
        default_start_date = timezone.localtime()
        parser.add_argument("command", help="commands: start, stop, show")
        parser.add_argument(
            "--title",
            default=default_title,
            help="Title of maintenance record")
        parser.add_argument(
            "--message",
            default=default_message,
            help="Use this as the message of maintenance record")
        parser.add_argument(
            "--start-date",
            default=default_start_date,
            help="Start date of maintenance record, default is now. Many "
                 "time formats are accepted. Use --dry-run to ensure "
                 "correct time.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Only print what would occur")

    def handle_start(self, **options):
        start_date = options['start_date']
        if isinstance(start_date, str):
            try:
                start_date = parse(start_date)
            except Exception as exc:
                raise CommandError("Error parsing start_date: {}".format(exc))

        record = MaintenanceRecord(
            title=options['title'],
            message=options['message'],
            start_date=start_date)
        if options['dry_run']:
            self.stdout.write("{}: {}".format(
                self.style.NOTICE("Dry run"), record))
        else:
            record.save()
            self.stdout.write("{}: {}".format(
                self.style.SUCCESS("Record created"), record))

    def handle_stop(self, **options):
        records = MaintenanceRecord.active()

        if not records:
            self.stdout.write("There are no active records")
            return

        for record in records:
            record.end_date = timezone.now()
            if options['dry_run']:
                self.stdout.write("{}: {}".format(
                    self.style.NOTICE("Dry run"), record))
                continue
            else:
                record.save()
                self.stdout.write("{}: {}".format(
                    self.style.SUCCESS("Record enddated"), record))

    def handle_show(self, **options):
        records = MaintenanceRecord.active()

        if not records:
            self.stdout.write("There are no active records")
            return

        for record in records:
            self.stdout.write(str(record))

    def handle(self, **options):
        cmd = options['command']
        handler = getattr(self, "handle_{}".format(cmd), _raise_unknown)
        handler(**options)


def _default_title():
    now = timezone.localdate()
    branch_name = git_branch()

    return "{0}/{1} ({2}) Maintenance".format(now.month, now.day,
                                              branch_name)

def _default_message():
    return "Atmosphere is down for a Scheduled Maintenance"

def _raise_unknown(*args, **options):
    cmd = options['command']
    raise CommandError("Unknown command: {}".format(cmd))
