
from uuid import uuid4
from datetime import timedelta

from django.db import models, transaction, DatabaseError
from django.db.models import ObjectDoesNotExist
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from threepio import logger

class EventTable(models.Model):

    """
    Used to keep a track of events
    """

    uuid = models.UUIDField(default=uuid4, unique=True, blank=True)
    agg_id = models.UUIDField(default=uuid4, unique=True, blank=True) # TODO : change to charfield
    name = models.CharField(max_length=128)
    payload = JSONField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "%s" % self.name
    
    class Meta:
        db_table = "event_table"
        app_label = "core"
