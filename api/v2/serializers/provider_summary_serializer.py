from core.models import Provider
from rest_framework import serializers
from .provider_type_serializer import ProviderTypeSerializer
from .platform_type_serializer import PlatformTypeSerializer

class ProviderSummarySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='location')

    class Meta:
        model = Provider
        fields = ('id', 'name', 'description', 'public', 'active', 'start_date', 'end_date', )
