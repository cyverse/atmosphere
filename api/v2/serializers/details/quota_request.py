from rest_framework import exceptions, serializers
from core.models import QuotaRequest, Quota, Identity, AtmosphereUser as User
from core.models.status_type import StatusType
from api.v2.serializers.summaries import (
    IdentitySummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    QuotaSummarySerializer,
    StatusTypeSummarySerializer
)


class UserRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return User.objects.all()

    def to_representation(self, value):
        user = User.objects.get(pk=value.pk)
        serializer = UserSummarySerializer(user, context=self.context)
        return serializer.data


class IdentityRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return Identity.objects.all()

    def to_representation(self, value):
        identity = Identity.objects.get(pk=value.pk)
        serializer = IdentitySummarySerializer(identity, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identity = data.get("id", None)
        else:
            identity = data
        try:
            return queryset.get(id=identity)
        except:
            raise exceptions.ValidationError(
                "Identity with id '%s' does not exist."
                % identity
            )


class QuotaRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return Quota.objects.all()

    def to_representation(self, value):
        if value.pk is None:
            return None

        quota = Quota.objects.get(pk=value.pk)
        serializer = QuotaSummarySerializer(quota, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identity = data.get("id", None)
        else:
            identity = data
        try:
            return queryset.get(id=identity)
        except:
            raise exceptions.ValidationError(
                "Quota with id '%s' does not exist."
                % identity
            )


class StatusTypeRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return StatusType.objects.all()

    def to_representation(self, value):
        status_type = StatusType.objects.get(pk=value.pk)
        serializer = StatusTypeSummarySerializer(status_type, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identity = data.get("id", None)
        else:
            identity = data

        try:
            return queryset.get(id=identity)
        except:
            raise exceptions.ValidationError(
                "StatusType with id '%s' does not exist."
                % identity
            )


class QuotaRequestSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.CharField(read_only=True)
    created_by = UserRelatedField(read_only=True)
    user = UserSummarySerializer(source='membership.identity.created_by', read_only=True)
    identity = IdentityRelatedField(source='membership.identity',
                                    queryset=Identity.objects.none())
    provider = ProviderSummarySerializer(source='membership.identity.provider', read_only=True)
    status = StatusTypeRelatedField(queryset=StatusType.objects.none(),
                                    allow_null=True,
                                    required=False)
    quota = QuotaRelatedField(queryset=Quota.objects.all(),
                              allow_null=True,
                              required=True)

    class Meta:
        model = QuotaRequest
        view_name = 'api_v2:quotarequest-detail'
        fields = (
            'id',
            'uuid',
            'url',
            'request',
            'description',
            'status',
            'created_by',
            'user',
            'identity',
            'provider',
            'admin_message',
            'quota'
        )


class UserQuotaRequestSerializer(serializers.HyperlinkedModelSerializer):
    quota = QuotaRelatedField(read_only=True)
    status = StatusTypeRelatedField(read_only=True)
    admin_message = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True)
    created_by = UserRelatedField(read_only=True)
    user = UserSummarySerializer(source='membership.identity.created_by', read_only=True)
    identity = IdentityRelatedField(source='membership.identity',
                                    queryset=Identity.objects.none())
    provider = ProviderSummarySerializer(source='membership.identity.provider', read_only=True)

    class Meta:
        model = QuotaRequest
        view_name = 'api_v2:quotarequest-detail'
        fields = (
            'id',
            'uuid',
            'url',
            'request',
            'description',
            'status',
            'created_by',
            'user',
            'identity',
            'provider',
            'admin_message',
            'quota'
        )
