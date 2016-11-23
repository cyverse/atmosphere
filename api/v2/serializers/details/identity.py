from core.models import Identity
from rest_framework import serializers
from api.v2.serializers.summaries import (
    QuotaSummarySerializer,
    CredentialSummarySerializer,
    AllocationSummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer
)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSummarySerializer(source='get_quota')
    credentials = CredentialSummarySerializer(many=True, source='credential_set')
    allocation = AllocationSummarySerializer(source='get_allocation')
    key = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:identity-detail',
    )

    def get_key(self, identity):
        return identity.get_key()

    def get_usage(self, identity):
        return identity.get_allocation_usage()


    class Meta:
        model = Identity
        fields = ('id',
                  'uuid',
                  'url',
                  'key',
                  'quota',
                  'credentials',
                  'allocation',
                  'usage',
                  'provider',
                  'user')
