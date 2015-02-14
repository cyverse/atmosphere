from core.models import ProviderMachine
from rest_framework import serializers
from ..summaries import ImageSummarySerializer, ProviderSummarySerializer, UserSummarySerializer


class ProviderMachineSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageSummarySerializer(source='application')
    provider = ProviderSummarySerializer()
    created_by = UserSummarySerializer()

    class Meta:
        model = ProviderMachine
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'url', 'image', 'provider', 'created_by', 'start_date', 'end_date')
