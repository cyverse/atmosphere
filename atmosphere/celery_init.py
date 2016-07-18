from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings
cwd_path = os.path.dirname(os.path.dirname(__file__))
os.environ.setdefault('PYTHONPATH', cwd_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atmosphere.settings')
os.environ.setdefault('PYTHONOPTIMIZE', '1')  #NOTE: Required to run ansible2 + celery + prefork concurrency

app = Celery('atmosphere')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(settings.INSTALLED_APPS, related_name='tasks')


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
