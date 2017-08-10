from core.models.identity import Identity
from rest_framework import serializers
from .quota_serializer import QuotaSerializer


class IdentitySerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='creator_name')
    credentials = serializers.ReadOnlyField(source='get_credentials')
    id = serializers.ReadOnlyField(source='uuid')
    provider_id = serializers.ReadOnlyField(source='provider_uuid')
    quota = QuotaSerializer(source='get_quota')

    class Meta:
        model = Identity
        fields = (
            'id',
            'created_by',
            'provider_id',
            'credentials',
            'quota'
        )
