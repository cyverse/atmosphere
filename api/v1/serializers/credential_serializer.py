from core.models.identity import Identity
from rest_framework import serializers


class CredentialDetailSerializer(serializers.ModelSerializer):
    credentials = serializers.ReadOnlyField(source='get_all_credentials')
    identity_id = serializers.ReadOnlyField(source='uuid')

    class Meta:
        model = Identity
        fields = ('credentials', 'identity_id')
