from rest_framework import serializers

from threepio import logger

from core.models import Identity, Quota
from api.v2.serializers.summaries import (
    QuotaSummarySerializer,
    CredentialSummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    GroupSummarySerializer
)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from core.events.serializers.quota_assigned import QuotaAssignedSerializer


class IdentitySerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaSummarySerializer(source='get_quota')
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

    def update(self, core_identity, validated_data):
        quota_id = validated_data.get('quota')
        quota = Quota.objects.get(id=quota_id)
        data = {'quota': quota.id, 'identity': core_identity.id}
        event_serializer = QuotaAssignedSerializer(data=data)
        if not event_serializer.is_valid():
            raise serializers.ValidationError(
                "Validation of EventSerializer failed with: %s"
                % event_serializer.errors)
        try:
            event_serializer.save()
        except Exception as exc:
            logger.exception("Unexpected error occurred during Event save")
            raise serializers.ValidationError(
                "Unexpected error occurred during Event save: %s" % exc)
        # Synchronous call to EventTable -> Set Quota for Identity's CloudProvider -> Save the Quota to Identity
        identity = Identity.objects.get(uuid=core_identity.uuid)
        return identity

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
                  'quota',
                  'credentials',
                  'usage',
                  'is_leader',
                  'provider',
                  'members',
                  'user')
