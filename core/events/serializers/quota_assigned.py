from rest_framework import serializers

from django.utils import timezone

from core.models import (
    AtmosphereUser, EventTable,
    Identity, Quota, ResourceRequest)
from core.serializers.fields import ModelRelatedField


class AtmosphereUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtmosphereUser
        fields = ("username",)


class QuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quota
        fields = (
            "cpu", "memory", "storage",
            "instance_count", "storage_count",
            "snapshot_count", "floating_ip_count",
            "port_count")


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Identity
        fields = ("uuid", "created_by", "provider")


class EventSerializer(serializers.Serializer):
    """
    EventSerializers take _anything they need_ as Input
    EventSerializers are responsible for validation
    EventSerializers will save events to the EventTable
    """
    def save(self):
        """
        On save:
          - The 'entity_id' and 'payload' of the event should be properly formatted and structured
          - EventSerializers should save and return the event:
            ```
                event = EventTable.create_event(
                    name="...",
                    entity_id=entity_id,
                    payload=event_payload)
                return event
            ```
        """
        raise NotImplemented("Implement this in the sub-class")
    pass


class QuotaAssignedSerializer(EventSerializer):
    quota = ModelRelatedField(
        queryset=Quota.objects.all(),
        serializer_class=QuotaSerializer,
        style={'base_template': 'input.html'})
    identity = ModelRelatedField(
        queryset=Identity.objects.all(),
        serializer_class=IdentitySerializer,
        style={'base_template': 'input.html'})
    update_method = serializers.CharField(default="API")
    timestamp = serializers.DateTimeField(default=timezone.now)

    def validate_update_method(self, value):
        value = value.lower()
        if value == 'api':
            return "API"
        elif value == 'admin':
            return "Admin"
        else:
            raise serializers.ValidationError("Invalid update_method (%s). Accepted values: API, Admin" % value)
        return value

    def save(self):
        # Properly structure the event data as a payload
        serialized_data = self.validated_data
        return_data = self.data
        entity_id = serialized_data['identity'].created_by.username
        event_payload = {
            'update_method': return_data['update_method'],
            'quota': return_data['quota'],
            'identity': return_data['identity']['uuid'],
            'timestamp': return_data['timestamp']
        }
        # Create the event in EventTable
        event = EventTable.create_event(
            name="quota_assigned",
            entity_id=entity_id,
            payload=event_payload)
        return event


class QuotaAssignedByResourceRequestSerializer(QuotaAssignedSerializer):
    resource_request = serializers.IntegerField()
    approved_by = ModelRelatedField(
        lookup_field='username',
        queryset=AtmosphereUser.objects.all(),
        serializer_class=AtmosphereUserSerializer,
        style={'base_template': 'input.html'})

    def validate_approved_by(self, test_value):
        if not AtmosphereUser.objects.filter(username=test_value).exists():
            raise serializers.ValidationError("Approved by username (%s) does not exist" % test_value)
        return test_value

    def validate_resource_request(self, test_value):
        if not ResourceRequest.objects.filter(id=test_value).exists():
            raise serializers.ValidationError("Resource request ID (%s) does not exist" % test_value)
        return test_value

    def save(self):
        # Properly structure the event data as a payload
        serialized_data = self.validated_data
        return_data = self.data
        entity_id = serialized_data['identity'].created_by.username
        event_payload = {
            'update_method': 'resource_request',
            'resource_request': return_data['resource_request'],
            'approved_by': serialized_data['approved_by'].username,
            'quota': return_data['quota'],
            'identity': return_data['identity']['uuid'],
            'timestamp': return_data['timestamp']
        }
        # Create the event in EventTable
        event = EventTable.create_event(
            name="quota_assigned",
            entity_id=entity_id,
            payload=event_payload)
        return event
