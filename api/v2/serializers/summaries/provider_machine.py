from core.models import ProviderMachine
from rest_framework import serializers
from .provider import ProviderSummarySerializer


class ProviderMachineSummarySerializer(serializers.HyperlinkedModelSerializer):
    provider = ProviderSummarySerializer(source='instance_source.provider')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')

    class Meta:
        model = ProviderMachine
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'url', 'provider', 'start_date', 'end_date')
