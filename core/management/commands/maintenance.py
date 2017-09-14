from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import MaintenanceRecord
from atmosphere.version import git_branch

 
def current_date():
    d = timezone.localdate()
    return (d.month, d.day)


def default_start_date():
    d = timezone.localdate()
    return timezone.datetime(d.year, d.month, d.day, 8, 0, 0,
        tzinfo=timezone.utc)

def _continue(val):
    option = 'n'
    if val is None or len(val) == 0:
        # Yes is the default, Example: [Y/n]
        option = 'y'
    elif len(val) > 0:
        option = val.lower()[0]

    return option == 'y'


class Command(BaseCommand):
    help = 'Allows starting and stopping maintenance'

    def add_arguments(self, parser):
        parser.add_argument("command", help="commands: start, stop")

    def _create_default_title(self):
        branch_name = git_branch()
        month, day = current_date()

        return "{0}/{1} ({2}) Maintenance".format(month, day, branch_name)

    def _gather_input(self):
        title = self._create_default_title()
        message = "Atmosphere is down for a Scheduled Maintenance"

        banner = "Default:"
        self.stdout.write(banner)
        self.stdout.write("-" * len(banner) + "\n")
        self.stdout.write("- title: {0}".format(title))
        self.stdout.write("- message: {0}".format(message))
        self.stdout.write("\n\n")

        new_title = raw_input("Provide desired title (ENTER to default): ")
        if len(new_title) > 0:
            title = new_title

        new_message = raw_input("Provide descriptive message (ENTER to default): ")
        if len(new_message) > 0:
            message = new_message

        return (title, message)

    def _gather_start_date(self):
        start_date = default_start_date()

        banner = "Default:"
        self.stdout.write(banner)
        self.stdout.write("-" * len(banner))
        self.stdout.write("- start date: {0}".format(start_date))
        self.stdout.write("\n")

        # ISO 8601 OR GET OUT! https://xkcd.com/1179/
        new_start_date = raw_input("Provider different start date, format: YYYY-MM-DD HH:MM\n(ENTER to default): ")
        if len(new_start_date) > 0:
            try:
                start_date = timezone.datetime.strptime(
                    new_start_date, "%Y-%m-%d %I:%M")
            except ValueError:
                self.stderr.write("Please use the ISO 8601 format:")
                self.stderr.write(" - https://xkcd.com/1179/")

        return start_date


    def handle_start(self):
        banner = "\nGathering Maintenance Information ..."
        self.stdout.write(banner)
        self.stdout.write("=" * len(banner))
        self.stdout.write("\n")

        while True:
            title, message = self._gather_input()

            self.stdout.write("\nTitle: {0}".format(title))
            self.stdout.write("Message: {0}".format(message))
            self.stdout.write("\n")

            option = raw_input("Continue? [Y/n] ")
            self.stdout.write("\n")

            if _continue(option):
                break

        while True:
            start_date = self._gather_start_date()

            self.stdout.write(
                "\n- Start date: {0}\n\n".format(start_date))

            option = raw_input("Continue? [Y/n] ")
            self.stdout.write("\n")

            if _continue(option):
                break

        new_record = MaintenanceRecord.objects.create(
            start_date=default_start_date())

        new_record.title = title
        new_record.message = message
        new_record.save()

        self.stdout.write(self.style.SUCCESS("MaintenanceRecord saved ..."))

        return True

    def handle_stop(self):
        records = MaintenanceRecord.active()

        self.stdout.write(
            "Preparing to process {0} records ...".format(len(records)))

        for record in records:
            self.stdout.write(" - End dating ... {0}".format(record))

            record.end_date = timezone.now()
            record.save()

        self.stdout.write("Done ...")

        return True

    def handle(self, *args, **options):
        cmd = options['command']

        result = False

        if cmd == 'start':
            result = self.handle_start()
        elif cmd == 'stop':
            result = self.handle_stop()
        else:
            self.stderr.write("Unknown command ...")

        if result:
            self.stdout.write(self.style.SUCCESS('Successfully ran ...'))
        else:
            self.stderr.write(" ... WHOA - an error occurred, I think!")
