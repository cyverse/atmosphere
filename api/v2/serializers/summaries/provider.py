from core.models import Provider
from rest_framework import serializers


class ProviderSummarySerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='location')

    class Meta:
        model = Provider
        view_name = 'api:v2:provider-detail'
        fields = ('id', 'uuid', 'url', 'name', 'description', 'public', 'active', 'start_date', 'end_date', )
