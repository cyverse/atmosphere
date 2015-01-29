from core.models.quota import Quota
from core.models.allocation import Allocation
from core.models.identity import Identity
from core.models.request import AllocationRequest, QuotaRequest, StatusType
from core.models.user import AtmosphereUser

from rest_framework import serializers


# Serializers
class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation


class AllocationRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True, source="uuid")
    created_by = serializers.SlugRelatedField(
        slug_field='username', source='created_by', read_only=True)
    status = serializers.SlugRelatedField(
        slug_field='name', source='status', read_only=True)

    class Meta:
        model = AllocationRequest
        exclude = ('uuid', 'membership')


class QuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quota
        exclude = ("id",)


class QuotaRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True, source="uuid", required=False)
    created_by = serializers.SlugRelatedField(
        slug_field='username', source='created_by',
        queryset=AtmosphereUser.objects.all())
    status = serializers.SlugRelatedField(
        slug_field='name', source='status',
        queryset=StatusType.objects.all())

    class Meta:
        model = QuotaRequest
        exclude = ('uuid', 'membership')


class IdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    credentials = serializers.Field(source='get_credentials')
    id = serializers.Field(source='uuid')
    provider_id = serializers.Field(source='provider_uuid')
    quota = QuotaSerializer(source='get_quota')
    allocation = AllocationSerializer(source='get_allocation')
    membership = serializers.Field(source='get_membership')

    class Meta:
        model = Identity
        fields = ('id', 'created_by', 'provider_id', 'credentials',
                  'membership', 'quota', 'allocation')
