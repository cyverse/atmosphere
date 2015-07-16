from core.models.identity import Identity
from rest_framework import serializers


class CleanedIdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='creator_name')
    id = serializers.ReadOnlyField(source='uuid')
    provider = serializers.ReadOnlyField(source='provider_uuid')

    class Meta:
        model = Identity
        fields = ('id', 'created_by', 'provider', )
