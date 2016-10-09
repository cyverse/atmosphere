from uuid import uuid4

from django.contrib.postgres.fields import JSONField
from django.core import exceptions
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.utils import timezone
from rest_framework import serializers
from threepio import logger

from core.hooks.allocation_source import (
    listen_before_allocation_snapshot_changes,
    listen_for_allocation_snapshot_changes,
    listen_for_user_snapshot_changes,
    listen_for_allocation_threshold_met,
    listen_for_allocation_overage,
    listen_for_instance_allocation_changes,
    listen_for_allocation_source_created,
    listen_for_user_allocation_source_assigned
)


class AllocationSourceCreatedEventSerializer(serializers.Serializer):
    source_id = serializers.CharField(required=True, allow_null=False, allow_blank=False, min_length=4, max_length=36)
    name = serializers.CharField(required=True, allow_null=False, allow_blank=False, min_length=2)
    compute_allowed = serializers.FloatField(required=True, allow_null=False, min_value=0.0)


class AllocationSourceAssignedEventSerializer(serializers.Serializer):
    source_id = serializers.CharField(required=True, allow_null=False, allow_blank=False, min_length=4, max_length=36)
    username = serializers.CharField(required=True, allow_null=False, allow_blank=False, min_length=2)


class AllocationSourceSnapshotEventSerializer(serializers.Serializer):
    allocation_source_id = serializers.CharField(required=True, allow_null=False, allow_blank=False, min_length=4,
                                                 max_length=36)
    compute_used = serializers.FloatField(required=True, allow_null=False, min_value=0.0)
    global_burn_rate = serializers.FloatField(required=True, allow_null=False, min_value=0.0)


class AllocationSourceThresholdMetEventSerializer(serializers.Serializer):
    allocation_source_id = serializers.CharField(required=True, allow_null=False, allow_blank=False, min_length=4,
                                                 max_length=36)
    actual_value = serializers.FloatField(required=True, min_value=0.0)
    threshold = serializers.FloatField(required=True, min_value=0.0)


EVENT_SERIALIZERS = {
    'allocation_source_snapshot': AllocationSourceSnapshotEventSerializer,
    'allocation_source_threshold_met': AllocationSourceThresholdMetEventSerializer,
    'allocation_source_created': AllocationSourceCreatedEventSerializer,
    'user_allocation_source_assigned': AllocationSourceAssignedEventSerializer
}


def validate_event_schema(event_name, event_payload):
    code = 'event_schema'
    try:
        serializer_class = EVENT_SERIALIZERS[event_name]
    except KeyError:
        limit_value = EVENT_SERIALIZERS.keys()
        message = 'Unrecognized event name: {}'.format(event_name)
        params = {'limit_value': limit_value, 'show_value': event_name, 'value': event_name}
        raise exceptions.ValidationError(message, code=code, params=params)
    try:
        serializer = serializer_class()
        assert isinstance(serializer, serializers.Serializer)
        validated_data = serializer.run_validation(data=event_payload)
        serialized_payload = validated_data
        return serialized_payload
    except Exception as e:
        logger.warn(e)
        message = 'Does not comply with event schema'
        limit_value = serializer_class
        params = {'limit_value': limit_value, 'show_value': event_payload, 'value': event_payload}
        raise exceptions.ValidationError(message, code=code, params=params)


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
        serialized_payload = validate_event_schema(name, payload)

        return EventTable.objects.create(
            name=name,
            entity_id=entity_id,
            payload=serialized_payload
        )

    def clean(self):
        validate_event_schema(self.name, self.payload)

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
post_save.connect(listen_for_user_allocation_source_assigned, sender=EventTable)
post_save.connect(listen_for_allocation_overage, sender=EventTable)
# post_save.connect(listen_for_changes, sender=EventTable)
post_save.connect(listen_for_allocation_threshold_met, sender=EventTable)
post_save.connect(listen_for_instance_allocation_changes, sender=EventTable)
post_save.connect(listen_for_allocation_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_user_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_allocation_source_created, sender=EventTable)
