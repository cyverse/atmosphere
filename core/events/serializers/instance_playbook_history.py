"""
Create events that look like:
name: instance_playbook_status_updated
entity_id: instance_id
payload:
{
   ansible_playbook: 'add_user_to_instance',
   arguments: ['sgregory'],
   status: 'queued/pending/running/deploy_error/error/completed',
   message: "<error_msg>/<empty>",
}
"""

from rest_framework import serializers

from django.utils import timezone

from core.models import (AtmosphereUser, EventTable, Instance)
from core.query import only_current
from core.serializers.fields import ModelRelatedField
from .base import EventSerializer
from .common import InstanceSerializer

ACCEPTED_STATUS_TYPES = ['queued', 'pending', 'running', 'deploy_error', 'error', 'completed']


def _create_instance_playbook_history_event(**kwargs):
    """
    This method streamlines the 'validate, raise if error, otherwise create an event' flow
    """
    serializer = InstancePlaybookHistoryUpdatedSerializer(data=kwargs)
    if not serializer.is_valid():
        raise Exception("Error on event creation: %s" % serializer.errors)
    return serializer.save()


def get_history_list_for_user(username, archived=False):
    user = AtmosphereUser.objects.get(username=username)
    qs = Instance.shared_with_user(user)
    if not archived:
        qs = qs.filter(only_current())
    instance_ids = qs.values_list('provider_alias', flat=True)
    history_qs = EventTable.objects.none()
    for instance_id in instance_ids:
        history_qs |= get_history_list_for_instance(instance_id)
    return history_qs


def get_history_list_for_instance(instance_id):
    all_playbook_histories = EventTable.instance_history_playbooks.filter(
        entity_id=instance_id)
    return all_playbook_histories


def get_last_history_for_instance(instance_id):
    all_playbook_histories = get_history_list_for_instance(instance_id)
    # FIXME: This ordering might not be accurate..
    # Instead, we might need to look at the timestamp within the payload...
    last_playbook_history = all_playbook_histories.order_by('-timestamp').first()
    return last_playbook_history


class InstancePlaybookHistoryUpdatedSerializer(EventSerializer):
    instance = ModelRelatedField(
        lookup_field="provider_alias",
        queryset=Instance.objects.all(),
        serializer_class=InstanceSerializer,
        style={'base_template': 'input.html'})
    playbook = serializers.CharField()
    arguments = serializers.JSONField()
    status = serializers.CharField()
    message = serializers.CharField(default="", required=False, allow_blank=True)
    timestamp = serializers.DateTimeField(default=timezone.now)

    def validate(self, data):
        validated_data = data.copy()
        status = validated_data.get('status', '').lower()
        if status not in ACCEPTED_STATUS_TYPES:
            raise serializers.ValidationError(
                "Invalid Status: %s not in list of ACCEPTED_STATUS_TYPES (%s)"
                % (status, ACCEPTED_STATUS_TYPES))
        return validated_data

    def save(self):
        serialized_data = self.validated_data
        instance_id = serialized_data['instance'].provider_alias
        playbook = serialized_data['playbook']
        arguments = serialized_data['arguments']
        status = serialized_data['status']
        message = serialized_data['message']
        timestamp = self.data['timestamp']  # Textual input, not datetime
        # Create event based on data
        entity_id = instance_id
        event_payload = {
            'ansible_playbook': playbook,
            'arguments': arguments,
            'status': status,
            'message': message,
            'timestamp': timestamp
        }
        # Create the event in EventTable
        event = EventTable.create_event(
            "instance_playbook_history_updated",
            event_payload,
            entity_id)
        return event
