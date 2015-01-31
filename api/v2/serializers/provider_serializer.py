from core.models import Provider
from rest_framework import serializers
from .provider_type_serializer import ProviderTypeSerializer
from .platform_type_serializer import PlatformTypeSerializer

class ProviderSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='location')
    type = ProviderTypeSerializer()
    virtualization = PlatformTypeSerializer()

    class Meta:
        model = Provider
        fields = ('id', 'name', 'description', 'public', 'active', 'type', 'virtualization', 'start_date', 'end_date', )
