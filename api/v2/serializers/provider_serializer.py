from core.models import Provider
from rest_framework import serializers
from .provider_type_serializer import ProviderTypeSerializer
from .platform_type_serializer import PlatformTypeSerializer
from .size_summary_serializer import SizeSummarySerializer


class ProviderSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='location')
    type = ProviderTypeSerializer()
    virtualization = PlatformTypeSerializer()
    sizes = SizeSummarySerializer(source='size_set', many=True)

    class Meta:
        model = Provider
        fields = ('id', 'name', 'description', 'public', 'active', 'type', 'virtualization', 'sizes', 'start_date', 'end_date', )
