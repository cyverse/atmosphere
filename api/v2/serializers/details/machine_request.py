from rest_framework import exceptions, serializers
from core.models import Instance, MachineRequest, Identity, AtmosphereUser as User, IdentityMembership
from core.models.status_type import StatusType
from api.v2.serializers.summaries import (
    AllocationSummarySerializer,
    IdentitySummarySerializer,
    InstanceSummarySerializer,
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


class InstanceRelatedField(serializers.RelatedField):
    def get_queryset(self):
        return Instance.objects.all()

    def to_representation(self, value):
        instance = Instance.objects.get(pk=value.pk)
        serializer = InstanceSummarySerializer(instance, context=self.context)
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


class MachineRequestSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.CharField(read_only=True)
    instance = InstanceRelatedField(read_only=True)
    #created_by = UserRelatedField(read_only=True)
    #user = UserSummarySerializer(
    #    source='membership.identity.created_by',
    #    read_only=True)
    #identity = IdentityRelatedField(source='membership.identity',
    #                                queryset=Identity.objects.none())
    #provider = ProviderSummarySerializer(
    #    source='membership.identity.provider',
    #    read_only=True)
    #created_by="AYY"
    #status = StatusTypeRelatedField(queryset=StatusType.objects.none(),
    #                                allow_null=True,
    #                                required=False)
    #quota = QuotaRelatedField(queryset=Quota.objects.all(),
    #                          allow_null=True,
    #                          required=False)

    #allocation = AllocationRelatedField(queryset=Allocation.objects.all(),
    #                                    allow_null=True,
    #                                    required=False)

    # TODO should be refactored to not use SerializerMethodField()
    #current_quota = serializers.SerializerMethodField()
    #current_allocation = serializers.SerializerMethodField()

    #def get_current_quota(self, request):
    #    user_membership = IdentityMembership.objects.get(
    #        id=request.membership_id)
    #    return user_membership.quota.id if user_membership.quota else None

    #def get_current_allocation(self, request):
    #    user_membership = IdentityMembership.objects.get(
    #        id=request.membership_id)
    #    return user_membership.allocation.id if user_membership.allocation else None

    class Meta:
        model = MachineRequest
        view_name = 'api:v2:machinerequest-detail'
        fields = (
            'id',
            'uuid',
            'url',
            'instance'
            #'request',
            #'description',
            #'status',
            #'created_by',
            #'user',
            #'identity',
            #'provider',
            #'admin_message',
            #'quota',
            #'allocation',
            #'current_quota',
            #'current_allocation'
        )


class UserMachineRequestSerializer(serializers.HyperlinkedModelSerializer):
    #quota = QuotaRelatedField(read_only=True)
    #allocation = AllocationRelatedField(read_only=True)
    #status = StatusTypeRelatedField(read_only=True)
    #print "USER"
    #admin_message = serializers.CharField(read_only=True)
    uuid = serializers.CharField(read_only=True)
    #created_by = UserRelatedField(read_only=True)
    #user = UserSummarySerializer(
    #    source='membership.identity.created_by',
    #    read_only=True)
    #identity = IdentityRelatedField(source='membership.identity',
    #                                queryset=Identity.objects.none())
    #provider = ProviderSummarySerializer(
    #    source='membership.identity.provider',
    #    read_only=True)

    class Meta:
        model = MachineRequest
        view_name = 'api:v2:machinerequest-detail'
        fields = (
            'id',
            'uuid',
            'url',
            #'request',
            #'description',
            #'status',
            #'created_by',
            #'user',
            #'identity',
            #'provider',
            #'admin_message',
            #'quota',
            #'allocation'
        )
