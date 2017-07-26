from __future__ import absolute_import, unicode_literals
import os
from celery import Celery


cwd_path = os.path.dirname(os.path.dirname(__file__))
os.environ.setdefault('PYTHONPATH', cwd_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atmosphere.settings')
os.environ.setdefault('PYTHONOPTIMIZE', '1')  #NOTE: Required to run ansible2 + celery + prefork concurrency -- removing will show `AttributeError: 'NoneType' object has no attribute 'terminate'`

app = Celery('atmosphere')
#app.conf.update(event_serializer='pickle', task_serializer='pickle', accept_content=['pickle'], result_serializer='pickle')


app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

#NOTE: Some settings are not being set properly.. so we'll override them.. again. here
# Load task modules from all registered Django app configs.
from atmosphere import settings
app.Task.resultrepr_maxsize = 2000

# Django-Celery secrets ( set inside atmosphere/settings/__init__.py )
app.conf.beat_schedule = settings.CELERYBEAT_SCHEDULE
app.conf.broker_url = settings.CELERY_BROKER_URL
app.conf.result_backend = settings.CELERY_RESULT_BACKEND
app.conf.task_send_sent_event = settings.CELERY_SEND_EVENTS
app.conf.accept_content = settings.CELERY_ACCEPT_CONTENT
app.conf.task_serializer = settings.CELERY_TASK_SERIALIZER
app.conf.result_serializer = settings.CELERY_RESULT_SERIALIZER
app.conf.event_serializer = settings.CELERY_EVENT_SERIALIZER
app.conf.task_routes = settings.CELERY_ROUTES
app.conf.worker_prefetch_multiplier = settings.CELERYD_PREFETCH_MULTIPLIER
app.conf.timezone = settings.CELERY_TIMEZONE
app.conf.worker_task_log_format = settings.CELERYD_TASK_LOG_FORMAT
app.conf.worker_log_format = settings.CELERYD_LOG_FORMAT

from kombu import serialization
serialization.registry._disabled_content_types.discard(u'application/x-python-serialize')

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
