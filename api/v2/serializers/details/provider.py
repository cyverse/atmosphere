from core.models import Provider, ProviderType, PlatformType
from rest_framework import serializers
from ..summaries import SizeSummarySerializer


class ProviderTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProviderType
        view_name = 'api_v2:providertype-detail'
        fields = ('id', 'url', 'name', 'start_date', 'end_date')


class PlatformTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PlatformType
        view_name = 'api_v2:platformtype-detail'
        fields = ('id', 'url', 'name', 'start_date', 'end_date')


class ProviderSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='location')
    type = ProviderTypeSerializer()
    virtualization = PlatformTypeSerializer()
    sizes = SizeSummarySerializer(source='size_set', many=True)

    class Meta:
        model = Provider
        view_name='api_v2:provider-detail'
        fields = ('id', 'url', 'name', 'description', 'public', 'active', 'type', 'virtualization', 'sizes', 'start_date', 'end_date', )
