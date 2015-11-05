from core.models import Identity
from rest_framework import serializers
from api.v2.serializers.summaries import (
    QuotaSummarySerializer,
    AllocationSummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer
)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSummarySerializer(source='get_quota')
    allocation = AllocationSummarySerializer(source='get_allocation')
    usage = serializers.SerializerMethodField()
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:identity-detail',
    )
    def get_usage(self, identity):
        return identity.get_allocation_usage()


    class Meta:
        model = Identity
        fields = ('id',
                  'uuid',
                  'url',
                  'quota',
                  'allocation',
                  'usage',
                  'provider',
                  'user')
