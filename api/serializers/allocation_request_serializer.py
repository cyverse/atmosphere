from core.models.request import AllocationRequest
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