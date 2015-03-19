from core.models.identity import Identity
from rest_framework import serializers


class CleanedIdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    # credentials = serializers.Field(source='get_credentials')
    id = serializers.ReadOnlyField(source='uuid')
    provider = serializers.ReadOnlyField(source='provider_uuid')
    # quota = serializers.Field(source='get_quota_dict')
    # allocation = serializers.Field(source='get_allocation_dict')
    # membership = serializers.Field(source='get_membership')

    class Meta:
        model = Identity
        fields = ('id', 'created_by', 'provider', )
