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
    identity = IdentitySummarySerializer()
    user = UserSummarySerializer(source='identity.created_by')
    provider = ProviderSummarySerializer(source='identity.provider')


    class Meta:
        model = IdentityMembership
        view_name = 'api:v2:identity-detail' # TODO: Make an identity-membership-detail
        fields = ('id',
                  #TODO: Re-add this in master:
                  #'url',
                  'quota',
                  'allocation',
                  'end_date',
                  'provider',
                  'identity',
                  'user')
