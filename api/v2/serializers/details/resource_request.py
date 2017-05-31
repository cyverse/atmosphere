from rest_framework import serializers
from core.models import ResourceRequest
from api.v2.serializers.summaries import UserSummarySerializer
from api.v2.serializers.fields import (
    IdentityRelatedField, StatusTypeRelatedField
)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ResourceRequestSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.CharField(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:resourcerequest-detail',
    )
    created_by = UserSummarySerializer(read_only=True)
    identity = IdentityRelatedField(source='membership.identity')
    status = StatusTypeRelatedField(allow_null=True, required=False)

    class Meta:
        model = ResourceRequest
        fields = (
            'id',
            'uuid',
            'url',
            'request',
            'description',
            'status',
            'created_by',
            'identity',
            'admin_message',
        )


class UserResourceRequestSerializer(ResourceRequestSerializer):
    def validate_status(self, value):
        if str(value) not in ["pending", "closed"]:
            raise serializers.ValidationError("Users can only open and close requests.")
        return value
