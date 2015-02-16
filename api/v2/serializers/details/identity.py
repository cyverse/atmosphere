from core.models import Identity
from rest_framework import serializers
from ..summaries import QuotaSummarySerializer, AllocationSummarySerializer, UserSummarySerializer

class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSummarySerializer(source='get_quota')
    allocation = AllocationSummarySerializer(source='get_allocation')
    user = UserSummarySerializer(source='created_by')

    class Meta:
        model = Identity
        view_name = 'api_v2:identity-detail'
        fields = ('id', 'url', 'quota', 'allocation', 'user')
