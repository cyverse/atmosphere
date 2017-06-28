from rest_framework import serializers

from threepio import logger

from core.models import (
    AtmosphereUser, Identity,
    Quota, ResourceRequest)
from core.serializers.fields import ModelRelatedField
from core.events.serializers.quota_assigned import QuotaAssignedByResourceRequestSerializer

from api.v2.views.base import AdminModelViewSet
from api.v2.serializers.summaries import (
    UserSummarySerializer, IdentitySummarySerializer,
    QuotaSummarySerializer)


class ResourceRequest_UpdateQuotaSerializer(serializers.Serializer):
    quota = ModelRelatedField(
        queryset=Quota.objects.all(),
        serializer_class=QuotaSummarySerializer,
        style={'base_template': 'input.html'})
    identity = ModelRelatedField(
        lookup_field='uuid',
        queryset=Identity.objects.all(),
        serializer_class=IdentitySummarySerializer,
        style={'base_template': 'input.html'})
    resource_request = serializers.PrimaryKeyRelatedField(
        queryset=ResourceRequest.objects.all())
    approved_by = ModelRelatedField(
        lookup_field='username',
        queryset=AtmosphereUser.objects.all(),
        serializer_class=UserSummarySerializer,
        style={'base_template': 'input.html'})

    def create(self, validated_data):
        """
        - Convert serializer into data for event_serializer
          - Save event_serializer
        - return serialized data
        """
        quota = validated_data.get('quota')
        user = validated_data.get('approved_by')
        resource_request = validated_data.get('resource_request')
        core_identity = validated_data.get('identity')
        data = {
            'quota': quota.id, 'identity': core_identity.id, 
            'resource_request': resource_request.id, 'approved_by': user.username
        }
        event_serializer = QuotaAssignedByResourceRequestSerializer(data=data)
        if not event_serializer.is_valid():
            raise serializers.ValidationError(
                "Validation of EventSerializer failed with: %s"
                % event_serializer.errors)
        try:
            event_serializer.save()
        except Exception as exc:
            logger.exception("Unexpected error occurred during Event save")
            raise serializers.ValidationError(
                "Unexpected error occurred during Event save: %s" % exc)
        # Synchronous call to EventTable -> Set Quota for Identity's CloudProvider -> Save the Quota to Identity
        identity = Identity.objects.get(uuid=core_identity.uuid)
        quota = identity.quota
        serialized_payload = {'identity': identity,
                'resource_request': resource_request,
                'approved_by': user,
                'quota': quota}
        return serialized_payload
