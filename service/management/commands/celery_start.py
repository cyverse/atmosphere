from django.core.management.base import BaseCommand
from subprocess import call

class Command(BaseCommand):
    help = 'Custom manage.py command to start celery.'

    def handle(self, *args, **options):
        call(["celery", "worker", "--app=atmosphere", "-n", "atmosphere-node_1@local", "--loglevel=INFO", "-O", "fair", "-Q", "default", "-c", "5", "--logfile=/var/log/celery/atmosphere-node_1.log", "--pidfile=/var/run/celery/atmosphere-node1.pid"])
