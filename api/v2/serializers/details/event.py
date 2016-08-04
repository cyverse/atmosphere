from core.models import EventTable
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from api.v2.serializers.summaries import UserSummarySerializer


class EventSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:event-detail',
    )

    def _validate_ias_event(self, payload):
        allocation_source_id = payload.get('allocation_source_id','')
        instance_id = payload.get('instance_id','')
        allocation_source = AllocationSource.objects.filter(source_id=allocation_source_id).first()
        instance = Instance.objects.filter(provider_alias=instance_id).first()
        if not allocation_source:
            raise serializers.ValidationError("AllocationSource with source_id=%s DoesNotExist" %  allocation_source_id)
        if not instance:
            raise serializers.ValidationError("Instance with provider_alias=%s DoesNotExist" %  instance_id)
        return True

    def validate(self, data):
        name = data['name']
        payload = data['payload']
        if name.lower() == 'instance_allocation_source_changed':
            self._validate_ias_event(payload)
        return super(EventSerializer, self).create(validated_data)

    class Meta:
        model = EventTable
        fields = (
            'id',
            'uuid',
            'url',
            'agg_id',
            'name',
            'payload',
            'timestamp',
        )
