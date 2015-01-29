from core.models.identity import Identity
from core.models.request import QuotaRequest, StatusType
from core.models.user import AtmosphereUser

from rest_framework import serializers


# Serializers
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
