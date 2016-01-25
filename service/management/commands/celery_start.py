from django.core.management.base import BaseCommand
from subprocess import call

class Command(BaseCommand):
    args = 'Arguments is not needed'
    help = 'Django admin custom command'

    def handle(self, *args, **options):
        call(["celery", "worker", "--app=atmosphere", "-n", "atmosphere-node_1@mickey.iplantc.org", "--loglevel=INFO", "-O", "fair", "-Q", "default", "-c", "5", "--logfile=/var/log/celery/atmosphere-node_1.log", "--pidfile=/var/run/celery/atmosphere-node1.pid"])
