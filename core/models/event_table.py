
from uuid import uuid4
from datetime import timedelta

from django.db import models, transaction, DatabaseError
from django.db.models import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_save
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from threepio import logger
from core.hooks.allocation_source import (
    listen_before_allocation_snapshot_changes,
    listen_for_allocation_snapshot_changes,
    listen_for_user_snapshot_changes,
    listen_for_allocation_threshold_met,
    listen_for_allocation_overage,
    listen_for_instance_allocation_changes,
    listen_for_allocation_source_created
)


class EventTable(models.Model):

    """
    Used to keep a track of events
    """

    uuid = models.UUIDField(default=uuid4, unique=True, blank=True)
    entity_id = models.CharField(max_length=255, default='', blank=True)
    name = models.CharField(max_length=128)
    payload = JSONField()
    timestamp = models.DateTimeField(default=timezone.now)

    @classmethod
    def create_event(cls, name, payload, entity_id):
        return EventTable.objects.create(
            name=name,
            entity_id=entity_id,
            payload=payload
        )

    def __str__(self):
        return "%s" % self.name

    class Meta:
        db_table = "event_table"
        app_label = "core"


# Save hooks
def listen_for_changes(sender, instance, created, **kwargs):
    """
    Ideally, this would be the master listener. On each save, it could contact all listeners and send them the payload.

    For now, it will do nothing.
    """
    return None

# Instantiate the hooks:
pre_save.connect(listen_before_allocation_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_allocation_overage, sender=EventTable)
#post_save.connect(listen_for_changes, sender=EventTable)
post_save.connect(listen_for_allocation_threshold_met, sender=EventTable)
post_save.connect(listen_for_instance_allocation_changes, sender=EventTable)
post_save.connect(listen_for_allocation_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_user_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_allocation_source_created, sender=EventTable)
