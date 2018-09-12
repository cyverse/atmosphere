from rest_framework import serializers
from core.models import ResourceRequest, StatusType
from core.models.status_type import get_status_type
from api.v2.serializers.summaries import (
    UserSummarySerializer, StatusTypeSummarySerializer
)
from core.serializers.fields import ModelRelatedField
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ResourceRequestSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.CharField(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:resourcerequest-detail',
    )
    created_by = UserSummarySerializer(read_only=True)
    status = ModelRelatedField(
        default=lambda: get_status_type(status="pending"),
        serializer_class=StatusTypeSummarySerializer,
        queryset=StatusType.objects.all(),
        lookup_field='id'
    )

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
            'admin_message',
            'start_date'
        )

class AdminResourceRequestSerializer(ResourceRequestSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:admin:resourcerequest-detail',
    )
