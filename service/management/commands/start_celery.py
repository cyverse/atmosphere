import os
from django.core.management.base import BaseCommand
from subprocess import call

class Command(BaseCommand):
    help = 'Custom manage.py command to start celery.'

    def handle(self, *args, **options):
        logfile = "celery_node.log"
        if not os.path.isfile(logfile):
            with open(logfile, 'w+') as f:
                f.close()
        call(("celery worker --app=atmosphere --loglevel=INFO -c 5 --logfile=%s" % logfile).split())
