from rest_framework import serializers

from core.models import (
    AtmosphereUser, Identity,
    Quota, ResourceRequest)
from core.serializers.fields import ModelRelatedField
from core.events.serializers.quota_assigned import QuotaAssignedByResourceRequestSerializer

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
        identity = validated_data.get('identity')

        # This api is designed to update a single identity's quota, instead we
        # update all identities for the user. This syncs the quota across all of
        # the user's active identities.
        for ident in [i for i in user.identity_set.all() if i.is_active()]:
            data = {
                'identity': ident.id,
                'resource_request': resource_request.id,
                'approved_by': user.username,
                'quota': quota.id
            }
            event_serializer = QuotaAssignedByResourceRequestSerializer(data=data)
            event_serializer.is_valid(raise_exception=True)
            event_serializer.save()

        return {
            'identity': identity,
            'resource_request': resource_request,
            'approved_by': user,
            'quota': quota
        }
