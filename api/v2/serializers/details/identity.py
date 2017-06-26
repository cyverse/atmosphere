from core.models import Group, Identity, Quota
from core.hooks.quota import set_quota_assigned
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


class UpdateIdentitySerializer(IdentitySerializer):
    approved_by = serializers.CharField(write_only=True)
    resource_request = serializers.UUIDField(write_only=True)
    provider = ProviderSummarySerializer(read_only=True)
    user = UserSummarySerializer(source='created_by', read_only=True)

    def update(self, core_identity, validated_data):
        # NOTE: Quota is the _only_ value that can be updated in Identity.
        quota_id = validated_data.get('quota')
        if 'id' in validated_data.get('quota'):
            quota_id = validated_data.get('quota').get('id')
        resource_request_id = validated_data.get('resource_request')
        approved_by = validated_data.get('approved_by')
        quota = Quota.objects.get(id=quota_id)
        set_quota_assigned(core_identity, quota, resource_request_id, approved_by)
        # Synchronous call to EventTable -> Set Quota in the Cloud -> Update the Quota for Identity
        identity = Identity.objects.get(uuid=core_identity.uuid)
        return identity

    class Meta:
        model = Identity
        fields = (
            'id',
            'uuid',
            'url',
            'quota',
            'allocation',
            'usage',
            'provider',
            'user',
            'approved_by',
            'resource_request')
