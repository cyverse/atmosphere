from core.models import Instance
from rest_framework import serializers
from ..summaries import IdentitySummarySerializer, UserSummarySerializer, ProviderSummarySerializer


class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    identity = IdentitySummarySerializer(source='created_by_identity')
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer(source='created_by_identity.provider')
    status = serializers.CharField(source='esh_status', read_only=True)

    class Meta:
        model = Instance
        view_name = 'api_v2:instance-detail'
        fields = (
            'id',
            'url',
            'name',
            'status',
            'ip_address',
            'shell',
            'vnc',
            'identity',
            'user',
            'provider',
            'start_date',
            'end_date',
        )
