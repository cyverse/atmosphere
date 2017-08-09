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


def lookup_access_list(instance_id):
    """
    Use EventTable to generate the 'current state' of usernames who _should_ be granted access to Instance
    """
    # FIXME: This call can be optimized in the future.
    # FIXME: This call is flawed, "Add, Remove, Add" will result in a "Remove" here.
    add_events = EventTable.objects.filter(
        name="add_share_instance_access",
        entity_id=instance_id)
    remove_events = EventTable.objects.filter(
        name="remove_share_instance_access",
        entity_id=instance_id)
    added_users = [payload['username'] for payload in add_events.values_list("payload", flat=True).distinct()]
    removed_users = [payload['username'] for payload in remove_events.values_list("payload", flat=True).distinct()]
    current_list = list(set(added_users) - set(removed_users))
    return current_list


def get_user_changes(instance_id, new_usernames):
    """
    Comparing a list of 'new usernames' to the current set of users,
    - Determine which usernames should be removed from the current set of users.
    - Determine which usernames should be added to the current set of users.
    """
    current_users = lookup_access_list(instance_id)
    users_to_add = list(set(new_usernames) - set(current_users))
    users_to_remove = list(set(current_users) - set(new_usernames))
    return (users_to_remove, users_to_add)


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
        username = validated_data.get('user').username.lower()
        instance_id = validated_data.get('instance').provider_alias
        current_users = lookup_access_list(instance_id)
        if username in current_users:
            raise serializers.ValidationError("Cannot add user: User %s is already in the instance access list" % username)
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
        username = validated_data.get('user').username.lower()
        instance_id = validated_data.get('instance').provider_alias
        current_users = lookup_access_list(instance_id)
        if username not in current_users:
            raise serializers.ValidationError("Cannot remove user: User %s is not in the instance access list" % username)
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
