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
    quota = QuotaSummarySerializer()
    allocation = AllocationSummarySerializer()
    identity_key = serializers.SerializerMethodField()
    identity = IdentitySummarySerializer()
    user = UserSummarySerializer(source='identity.created_by')
    provider = ProviderSummarySerializer(source='identity.provider')
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:identitymembership-detail',
    )

    def get_identity_key(self, identity_membership):
        return identity_membership.identity.get_credential('key')

    class Meta:
        model = IdentityMembership
        fields = ('id',
                  'url',
                  'quota',
                  'allocation',
                  'end_date',
                  'provider',
                  'identity',
                  'identity_key',
                  'user')
