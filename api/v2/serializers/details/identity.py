from core.models import (
    Group,
    Identity
)
from rest_framework import serializers
from api.v2.serializers.summaries import (
    QuotaSummarySerializer,
    CredentialSummarySerializer,
    AllocationSummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    GroupSummarySerializer
)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from api.v2.serializers.fields.base import ModelRelatedField


class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSummarySerializer(source='get_quota')
    allocation = AllocationSummarySerializer(source='get_allocation')
    usage = serializers.SerializerMethodField()
    credentials = CredentialSummarySerializer(many=True, source='credential_set')
    key = serializers.SerializerMethodField()
    is_leader = serializers.SerializerMethodField()
    user = UserSummarySerializer(source='created_by')
    members = GroupSummarySerializer(
        source='get_membership',
        many=True, read_only=True)
    provider = ProviderSummarySerializer()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:identity-detail',
    )

    def get_usage(self, identity):
        return -1

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


    class Meta:
        model = Identity
        fields = ('id',
                  'uuid',
                  'url',
                  'key',
                  'allocation',
                  'quota',
                  'credentials',
                  'usage',
                  'is_leader',
                  'provider',
                  'members',
                  'user')
