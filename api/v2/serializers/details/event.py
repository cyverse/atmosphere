from core.models import EventTable, AllocationSource, Instance
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class EventSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:event-detail',
    )

    def _validate_ias_event(self, entity_id, payload):
        allocation_source_id = payload.get('allocation_source_id', '')
        instance_id = payload.get('instance_id', '')
        user = self._get_request_user()
        if entity_id != user.username:
            raise serializers.ValidationError(
                "Expected entity ID to be the Username: %s, Received: %s"
                % (user.username, entity_id))
        if not user:
            raise serializers.ValidationError("Request user was not found")
        allocation_source = AllocationSource.for_user(user=user).filter(
            source_id=allocation_source_id).first()
        instance = Instance.for_user(user=user).filter(provider_alias=instance_id).first()
        if not allocation_source:
            raise serializers.ValidationError(
                "AllocationSource with source_id=%s DoesNotExist"
                % allocation_source_id)
        if not instance:
            raise serializers.ValidationError(
                "Instance with provider_alias=%s DoesNotExist"
                % instance_id)
        return True

    def _get_request_user(self):
        if 'request' not in self.context:
            raise ValueError("Expected 'request' context for this serializer")
        return self.context['request'].user

    def validate(self, data):
        name = data['name']
        entity_id = data['entity_id']
        payload = data['payload']
        if name.lower() == 'instance_allocation_source_changed':
            self._validate_ias_event(entity_id, payload)
        else:
            raise serializers.ValidationError(
                "Unknown event type %s" % name
            )
        return super(EventSerializer, self).validate(data)

    class Meta:
        model = EventTable
        fields = (
            'id',
            'uuid',
            'url',
            'entity_id',
            'name',
            'payload',
            'timestamp',
        )
