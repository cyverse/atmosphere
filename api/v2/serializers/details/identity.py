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
    usage = serializers.SerializerMethodField()
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer()

    def get_usage(self, identity):
        return identity.get_allocation_usage()


    class Meta:
        model = Identity
        view_name = 'api:v2:identity-detail'
        fields = ('id',
                  'uuid',
                  'url',
                  'quota',
                  'allocation',
                  'usage',
                  'provider',
                  'user')
