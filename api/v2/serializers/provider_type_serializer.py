from core.models import ProviderType
from rest_framework import serializers


class ProviderTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProviderType
        view_name = 'api_v2:providertype-detail'
        fields = ('id', 'url', 'name', 'start_date', 'end_date')
