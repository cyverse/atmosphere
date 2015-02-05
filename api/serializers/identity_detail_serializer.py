from core.models.identity import Identity
from rest_framework import serializers


class IdentityDetailSerializer(serializers.ModelSerializer):
    # created_by = serializers.CharField(source='creator_name')
    quota = serializers.Field(source='get_quota_dict')
    provider_id = serializers.Field(source='provider.uuid')
    id = serializers.Field(source="uuid")

    class Meta:
        model = Identity
        fields = ('id', 'provider_id', 'quota')
