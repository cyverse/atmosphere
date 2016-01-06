from core.models import IdentityMembership
from rest_framework import serializers
from api.v2.serializers.summaries import (
    AllocationSummarySerializer,
    IdentitySummarySerializer,
    ProviderSummarySerializer,
    QuotaSummarySerializer,
    UserSummarySerializer,
)

class IdentityMembershipSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:identitymembership-detail',
    )
    quota = QuotaSummarySerializer()
    allocation = AllocationSummarySerializer()
    identity = IdentitySummarySerializer()
    user = UserSummarySerializer(source='identity.created_by')
    provider = ProviderSummarySerializer(source='identity.provider')
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:identitymembership-detail',
    )

    class Meta:
        model = IdentityMembership
        fields = ('id',
                  'url',
                  'quota',
                  'allocation',
                  'end_date',
                  'provider',
                  'identity',
                  'user')
