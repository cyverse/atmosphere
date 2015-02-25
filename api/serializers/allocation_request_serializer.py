from core.models import Allocation, AtmosphereUser
from core.models.request import AllocationRequest
from core.models.status_type import StatusType
from rest_framework import serializers


class AllocationRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True, source="uuid")
    created_by = serializers.SlugRelatedField(
        slug_field='username', read_only=True)
    status = serializers.SlugRelatedField(
        slug_field='name', read_only=True)

    class Meta:
        model = AllocationRequest
        exclude = ('uuid', 'membership')


class ResolveAllocationRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True, source="uuid", required=False)

    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=StatusType.objects.all())

    created_by = serializers.SlugRelatedField(
        slug_field='username',
        queryset=AtmosphereUser.objects.all())

    allocation = serializers.SlugRelatedField(
        slug_field='id',
        queryset=Allocation.objects.all())

    class Meta:
        model = AllocationRequest
        exclude = ('uuid', 'membership')
