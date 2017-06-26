from uuid import uuid4

from django.db import models
from django.db.models.signals import post_save, pre_save
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from core.hooks.allocation_source import (
    listen_before_allocation_snapshot_changes,
    listen_for_allocation_snapshot_changes,
    listen_for_user_snapshot_changes,
    listen_for_allocation_threshold_met,
    listen_for_instance_allocation_changes,
    listen_for_allocation_source_created_or_renewed,
    listen_for_user_allocation_source_deleted,
    listen_for_user_allocation_source_created,
    #listen_for_allocation_source_created,
    #listen_for_user_allocation_source_assigned,
    #listen_for_user_allocation_source_removed,
    #listen_for_allocation_source_renewed,
    listen_for_allocation_source_renewal_strategy_changed,
    listen_for_allocation_source_name_changed,
    listen_for_allocation_source_compute_allowed_changed,
    listen_for_allocation_source_removed,
    listen_for_instance_allocation_removed
)
from core.hooks.quota import listen_for_quota_assigned
from threepio import logger


class EventTable(models.Model):

    """
    Used to keep a track of events
    """

    uuid = models.UUIDField(default=uuid4, unique=True, blank=True)
    entity_id = models.CharField(max_length=255, default='', blank=True, db_index=True)
    name = models.CharField(max_length=128, db_index=True)
    payload = JSONField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    @classmethod
    def create_event(cls, name, payload, entity_id):
        logger.info("Creating new event: %s\tPayload: %s" % (name, payload))
        return EventTable.objects.create(
            name=name,
            entity_id=entity_id,
            payload=payload
        )

    def __str__(self):
        return "%s" % self.name

    def __unicode__(self):
        return unicode(self.name)

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
post_save.connect(listen_for_allocation_threshold_met, sender=EventTable)
post_save.connect(listen_for_instance_allocation_changes, sender=EventTable)
post_save.connect(listen_for_allocation_source_created_or_renewed, sender=EventTable)
post_save.connect(listen_for_allocation_source_compute_allowed_changed, sender=EventTable)
post_save.connect(listen_for_user_allocation_source_created, sender=EventTable)
post_save.connect(listen_for_user_allocation_source_deleted, sender=EventTable)
pre_save.connect(listen_before_allocation_snapshot_changes, sender=EventTable)
#post_save.connect(listen_for_user_allocation_source_assigned, sender=EventTable)
#post_save.connect(listen_for_user_allocation_source_removed, sender=EventTable)
post_save.connect(listen_for_instance_allocation_removed, sender=EventTable)
post_save.connect(listen_for_allocation_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_user_snapshot_changes, sender=EventTable)
#post_save.connect(listen_for_allocation_source_renewed, sender=EventTable)
post_save.connect(listen_for_allocation_source_renewal_strategy_changed, sender=EventTable)
#post_save.connect(listen_for_allocation_source_created, sender=EventTable)
post_save.connect(listen_for_allocation_source_name_changed, sender=EventTable)
post_save.connect(listen_for_allocation_source_removed,sender=EventTable)
