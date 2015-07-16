from core.models.identity import Identity
from rest_framework import serializers


class IdentityDetailSerializer(serializers.ModelSerializer):
    quota = serializers.ReadOnlyField(source='get_quota_dict')
    provider_id = serializers.ReadOnlyField(source='provider.uuid')
    id = serializers.ReadOnlyField(source="uuid")

    class Meta:
        model = Identity
        fields = ('id', 'provider_id', 'quota')
