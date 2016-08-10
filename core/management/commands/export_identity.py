from django.core.management.base import BaseCommand, CommandError
from core.models import Identity


class Command(BaseCommand):
    help = 'Exports the specified identity to a file'

    def add_arguments(self, parser):
        parser.add_argument("--identity-id", type=int, help="Atmosphere identity"
                            " ID to export")
        parser.add_argument("--file", help="The file location to write identity export data")

    def handle(self, *args, **options):
        filename = options['file']
        identity_id = options['identity_id']
        try:
            identity = Identity.objects.get(id=identity_id)
            identity.export_to_file(filename)
        except Identity.DoesNotExist:
            raise CommandError('Identity ID "%s" does not exist' % identity_id)
        self.stdout.write(self.style.SUCCESS('Successfully exported identity to file "%s"' % filename))
