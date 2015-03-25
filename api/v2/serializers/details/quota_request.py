from core.models import QuotaRequest, Quota, Identity, AtmosphereUser as User
from rest_framework import serializers
from api.v2.serializers.summaries import (
    IdentitySummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    QuotaSummarySerializer
)


class UserRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return User.objects.all()

    def to_representation(self, value):
        user = User.objects.get(pk=value.pk)
        serializer = UserSummarySerializer(user, context=self.context)
        return serializer.data


class IdentityRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Identity.objects.all()

    def to_representation(self, value):
        identity = Identity.objects.get(pk=value.pk)
        serializer = IdentitySummarySerializer(identity, context=self.context)
        return serializer.data


class QuotaRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Quota.objects.all()

    def to_representation(self, value):
        if value.pk is None:
            return None

        quota = Quota.objects.get(pk=value.pk)
        serializer = QuotaSummarySerializer(quota, context=self.context)
        return serializer.data


class QuotaRequestSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.CharField(read_only=True)
    created_by = UserRelatedField(read_only=True)
    user = UserSummarySerializer(source='membership.identity.created_by', read_only=True)
    identity = IdentityRelatedField(source='membership.identity', queryset=Identity.objects.none())
    provider = ProviderSummarySerializer(source='membership.identity.provider', read_only=True)
    quota = QuotaRelatedField(queryset=Quota.objects.all())

    class Meta:
        model = QuotaRequest
        view_name = 'api_v2:quotarequest-detail'
        fields = (
            'id',
            'uuid',
            'url',
            'admin_message',
            'request',
            'description',
            'created_by',
            'user',
            'identity',
            'provider',
            'quota'
        )
