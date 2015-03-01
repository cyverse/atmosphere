from core.models import Instance, Size
from rest_framework import serializers
from .identity import IdentitySummarySerializer
from .size import SizeSummarySerializer


class InstanceSummarySerializer(serializers.HyperlinkedModelSerializer):
    identity = IdentitySummarySerializer(source='created_by_identity')
    user = serializers.PrimaryKeyRelatedField(source='created_by', read_only=True)
    provider = serializers.PrimaryKeyRelatedField(source='created_by_identity.provider', read_only=True)
    status = serializers.CharField(source='esh_status', read_only=True)
    size = serializers.SerializerMethodField()

    def get_size(self, obj):
        size_alias = obj.esh_size()
        provider_id = obj.created_by_identity.provider_id
        size = Size.objects.get(alias=size_alias, provider=provider_id)
        serializer = SizeSummarySerializer(size, context=self.context)
        return serializer.data

    class Meta:
        model = Instance
        view_name = 'api_v2:instance-detail'
        fields = (
            'id',
            'url',
            'name',
            'status',
            'size',
            'ip_address',
            'shell',
            'vnc',
            'identity',
            'user',
            'provider',
            'start_date',
            'end_date',
        )
