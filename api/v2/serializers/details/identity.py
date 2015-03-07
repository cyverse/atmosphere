from core.models import Identity
from rest_framework import serializers
from api.v2.serializers.summaries import (
    QuotaSummarySerializer,
    AllocationSummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer
)


class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSummarySerializer(source='get_quota')
    allocation = AllocationSummarySerializer(source='get_allocation')
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer()

    class Meta:
        model = Identity
        view_name = 'api_v2:identity-detail'
        fields = ('id', 'uuid', 'url', 'quota', 'allocation', 'provider', 'user')
