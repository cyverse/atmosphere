import subprocess
from django.core.management.base import BaseCommand
from subprocess import call

class Command(BaseCommand):
    help = 'Custom manage.py command to start celery.'

    def handle(self, *args, **options):
        call("celery worker --app=atmosphere --loglevel=INFO -c 5 --logfile='celery_node.log".split())
