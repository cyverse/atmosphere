from core.models import Instance, Size
from rest_framework import serializers
from ..summaries import IdentitySummarySerializer, UserSummarySerializer, ProviderSummarySerializer, \
    SizeSummarySerializer


class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    identity = IdentitySummarySerializer(source='created_by_identity')
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer(source='created_by_identity.provider')
    status = serializers.CharField(source='esh_status', read_only=True)
    projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
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
            'projects',
            'start_date',
            'end_date'
        )
