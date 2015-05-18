from rest_framework import exceptions, serializers
from core.models import AllocationRequest, Allocation, Identity, AtmosphereUser as User
from core.models.status_type import StatusType
from api.v2.serializers.summaries import (
    IdentitySummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    AllocationSummarySerializer,
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


class AllocationRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return Allocation.objects.all()

    def to_representation(self, value):
        if value.pk is None:
            return None

        quota = Allocation.objects.get(pk=value.pk)
        serializer = AllocationSummarySerializer(quota, context=self.context)
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
                "Allocation with id '%s' does not exist."
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


class AllocationRequestSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.CharField(read_only=True)
    created_by = UserRelatedField(read_only=True)
    user = UserSummarySerializer(source='membership.identity.created_by',
                                 read_only=True)
    identity = IdentityRelatedField(source='membership.identity',
                                    queryset=Identity.objects.none())
    provider = ProviderSummarySerializer(source='membership.identity.provider',
                                         read_only=True)
    status = StatusTypeRelatedField(queryset=StatusType.objects.none(),
                                    allow_null=True,
                                    required=False)
    allocation = AllocationRelatedField(queryset=Allocation.objects.all(),
                                        allow_null=True,
                                        required=False)

    class Meta:
        model = AllocationRequest
        view_name = 'api_v2:allocationrequest-detail'
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
            'allocation'
        )


class UserAllocationRequestSerializer(serializers.HyperlinkedModelSerializer):
    allocation = AllocationRelatedField(read_only=True)
    status = StatusTypeRelatedField(read_only=True)
    admin_message = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True)
    created_by = UserRelatedField(read_only=True)
    user = UserSummarySerializer(source='membership.identity.created_by',
                                 read_only=True)
    identity = IdentityRelatedField(source='membership.identity',
                                    queryset=Identity.objects.none())
    provider = ProviderSummarySerializer(source='membership.identity.provider',
                                         read_only=True)

    class Meta:
        model = AllocationRequest
        view_name = 'api_v2:allocationrequest-detail'
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
            'allocation'
        )
