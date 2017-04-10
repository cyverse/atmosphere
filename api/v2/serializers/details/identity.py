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
    is_leader = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:identity-detail',
    )

    def get_is_leader(self, identity):
        """
        Returns true/false if the user requesting the object is the leader.
        """
        if self.context:
            if 'request' in self.context:
                user = self.context['request'].user
            elif 'user' in self.context:
                user = self.context['user']
            else:
                user = None
        if user == identity.created_by:
            return True
        return Identity.shared_with_user(user, is_leader=True).filter(id=identity.id).exists()

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
                  'is_leader',
                  'quota',
                  'credentials',
                  'allocation',
                  'usage',
                  'provider',
                  'user')
