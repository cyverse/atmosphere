from rest_framework import serializers
from threepio import logger

from django.utils import timezone

from core.models import (AtmosphereUser, EventTable, Instance, InstanceAccess)
from core.serializers.fields import ModelRelatedField
from .base import EventSerializer
from .common import AtmosphereUserSerializer, InstanceSerializer
from django.db.models import Sum, Count


def list_access_for(username):
    """
    Look at EventTable for all instances that 'username' is currently allowed to access
    """
    return InstanceAccess.shared_with_user(username)


class InstanceAccessSerializer(EventSerializer):
    instance = ModelRelatedField(
        lookup_field="provider_alias",
        queryset=Instance.objects.all(),
        serializer_class=InstanceSerializer,
        style={'base_template': 'input.html'})
    user = ModelRelatedField(
        lookup_field="username",
        queryset=AtmosphereUser.objects.all(),
        serializer_class=AtmosphereUserSerializer,
        style={'base_template': 'input.html'})
    timestamp = serializers.DateTimeField(default=timezone.now)
    def validate(self, data):
        raise NotImplemented("This serializer should not be called directly. The sub-class should implement this method.")

class AddInstanceAccessSerializer(InstanceAccessSerializer):

    def validate(self, data):
        validated_data = data.copy()
        return validated_data

    def save(self):
        # Properly structure the event data as a payload
        serialized_data = self.validated_data
        instance_id = serialized_data['instance'].provider_alias
        username = serialized_data['user'].username
        timestamp = self.data['timestamp']
        entity_id = instance_id
        event_payload = {
            'instance_id': instance_id,
            'username': username,
            'timestamp': timestamp
        }
        # Create the event in EventTable
        event = EventTable.create_event(
            "add_share_instance_access",
            event_payload,
            entity_id)
        return event

class RemoveInstanceAccessSerializer(InstanceAccessSerializer):

    def validate(self, data):
        validated_data = data.copy()
        return validated_data

    def save(self):
        # Properly structure the event data as a payload
        serialized_data = self.validated_data
        instance_id = serialized_data['instance'].provider_alias
        username = serialized_data['user'].username
        timestamp = self.data['timestamp']
        entity_id = instance_id
        event_payload = {
            'instance_id': instance_id,
            'username': username,
            'timestamp': timestamp
        }
        # Create the event in EventTable
        event = EventTable.create_event(
            "remove_share_instance_access",
            event_payload,
            entity_id)
        return event
