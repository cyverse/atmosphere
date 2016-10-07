
from uuid import uuid4
from datetime import timedelta

import avro
import avro_json_serializer
from django.core import exceptions
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
    listen_for_allocation_source_created,
    listen_for_user_allocation_source_assigned
)

ALLOCATION_SOURCE_CREATED = avro.schema.make_avsc_object(
    {
        'namespace': 'org.cyverse.atmosphere.event',
        'type': 'record',
        'name': 'allocation_source_created',
        'fields': [
            {
                'name': 'source_id',
                'type': 'string'
            },
            {
                'name': 'name',
                'type': 'string'
            },
            {
                'name': 'compute_allowed',
                'type': 'float'
            }
        ]
    }
)
USER_ALLOCATION_SOURCE_ASSIGNED = avro.schema.make_avsc_object(
    {
        'namespace': 'org.cyverse.atmosphere.event',
        'type': 'record',
        'name': 'user_allocation_source_assigned',
        'fields': [
            {
                'name': 'source_id',
                'type': 'string'
            },
            {
                'name': 'username',
                'type': 'string'
            }
        ]
    }
)

ALLOCATION_SOURCE_SNAPSHOT_SCHEMA = avro.schema.make_avsc_object(
    {
        'namespace': 'org.cyverse.atmosphere.event',
        'type': 'record',
        'name': 'allocation_source_snapshot',
        'fields': [
            {
                'name': 'allocation_source_id',
                'type': 'string'
            },
            {
                'name': 'compute_used',
                'type': 'float'
            },
            {
                'name': 'global_burn_rate',
                'type': 'float'
            }
        ]
    }
)

ALLOCATION_SOURCE_THRESHOLD_MET = avro.schema.make_avsc_object(
    {
        'namespace': 'org.cyverse.atmosphere.event',
        'type': 'record',
        'name': 'allocation_source_threshold_met',
        'fields': [
            {
                'name': 'allocation_source_id',
                'type': 'string'
            },
            {
                'name': 'actual_value',
                'type': 'float'
            },
            {
                'name': 'threshold',
                'type': 'float'
            }
        ]
    }
)

EVENT_SCHEMAS = {
    'allocation_source_snapshot': ALLOCATION_SOURCE_SNAPSHOT_SCHEMA,
    'allocation_source_threshold_met': ALLOCATION_SOURCE_THRESHOLD_MET,
    'allocation_source_created': ALLOCATION_SOURCE_CREATED,
    'user_allocation_source_assigned': USER_ALLOCATION_SOURCE_ASSIGNED
}


def validate_event_schema(event_name, event_payload):
    code = 'event_schema'
    try:
        event_schema = EVENT_SCHEMAS[event_name]
    except KeyError:
        limit_value = EVENT_SCHEMAS.keys()
        message = 'Unrecognized event name: {}'.format(event_name)
        params = {'limit_value': limit_value, 'show_value': event_name, 'value': event_name}
        raise exceptions.ValidationError(message, code=code, params=params)
    try:
        serializer = avro_json_serializer.AvroJsonSerializer(event_schema)
        serialized_payload = serializer.to_ordered_dict(event_payload)
        return serialized_payload
    except Exception as e:
        logger.warn(e)
        message = 'Does not comply with event schema'
        limit_value = event_schema
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
#post_save.connect(listen_for_changes, sender=EventTable)
post_save.connect(listen_for_allocation_threshold_met, sender=EventTable)
post_save.connect(listen_for_instance_allocation_changes, sender=EventTable)
post_save.connect(listen_for_allocation_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_user_snapshot_changes, sender=EventTable)
post_save.connect(listen_for_allocation_source_created, sender=EventTable)
