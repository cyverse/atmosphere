from core.models import Size
from rest_framework import serializers
from ..summaries import ProviderSummarySerializer


class SizeSerializer(serializers.HyperlinkedModelSerializer):
    provider = ProviderSummarySerializer()

    class Meta:
        model = Size
        view_name = 'api_v2:size-detail'
        fields = ('id', 'url', 'alias', 'name', 'cpu', 'disk', 'mem', 'active', 'provider', 'start_date', 'end_date')
