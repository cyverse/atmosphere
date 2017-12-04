from rest_framework import serializers
from core.models import InstancePlaybookSnapshot, EventTable
from threepio import logger

from api.v2.serializers.summaries import (
    InstanceSuperSummarySerializer
)


class PayloadField(serializers.Field):
    def __init__(self, payload_class=None, payload_field=None, *args, **kwargs):
        self.payload_field = payload_field
        self.payload_class = payload_class
        super(PayloadField, self).__init__(*args, **kwargs)

    def to_representation(self, payload_obj):
        """
        Transform the *outgoing* native value into primitive data.
        """
        data = payload_obj.get(self.payload_field)
        return data

    def to_internal_value(self, data):
        """
        Given "raw data" return the expected "object"
        """
        if self.payload_class:
            return self.payload_class().to_representation(data)
        return data


class InstancePlaybookHistorySerializer(serializers.ModelSerializer):
    instance = serializers.CharField(source="entity_id")
    playbook_name = PayloadField(
        source="payload",
        payload_field="ansible_playbook"
    )
    arguments = PayloadField(
        source="payload",
        payload_field="arguments",
        payload_class=serializers.JSONField)
    status = PayloadField(
        source="payload",
        payload_field="status")
    message = PayloadField(
        source="payload",
        payload_field="message")
    timestamp = PayloadField(
        source="payload",
        payload_field="timestamp",
        payload_class=serializers.DateTimeField)

    class Meta:
        model = EventTable
        fields = (
            "instance",
            "playbook_name",
            "arguments",
            "status",
            "message",
            "timestamp"
        )


class InstancePlaybookSnapshotSerializer(serializers.ModelSerializer):
    instance = InstanceSuperSummarySerializer()
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:instance_playbook-detail',
    )

    def update(self, snapshot, validated_data):
        logger.info("Updating snapshot %s" % snapshot)
        if validated_data.get('status') == 'queued':
            from service.instance_access import retry_playbook_with_args
            logger.info("Retrying instance access")
            retry_playbook_with_args(snapshot)
            snapshot.status = validated_data.get('status')
        return snapshot

    class Meta:
        model = InstancePlaybookSnapshot
        fields = ("id", "instance", "playbook_name", "playbook_arguments", "status", "url")
