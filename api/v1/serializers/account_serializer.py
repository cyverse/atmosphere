from core.models.group import IdentityMembership
from rest_framework import serializers


class AccountSerializer(serializers.ModelSerializer):
    credentials = serializers.ReadOnlyField(source='identity.get_credentials')
    identity_id = serializers.ReadOnlyField(source='identity.uuid')
    provider_id = serializers.ReadOnlyField(source='identity.provider_uuid')
    group_name = serializers.ReadOnlyField(source='member.name')

    class Meta:
        model = IdentityMembership
        fields = ('identity_id', 'credentials', 'provider_id', 'group_name')
