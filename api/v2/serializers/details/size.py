from core.models import Size
from rest_framework import serializers
from api.v2.serializers.summaries import ProviderSummarySerializer


class SizeSerializer(serializers.HyperlinkedModelSerializer):
    provider = ProviderSummarySerializer()

    class Meta:
        model = Size
        view_name = 'api:v2:size-detail'
        fields = ('id', 'url', 'alias', 'name', 'cpu', 'disk', 'root', 'mem', 'active', 'provider', 'start_date', 'end_date')
