from core.models import ProviderMachine
from rest_framework import serializers


class ProviderMachineSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ProviderMachine
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'url', 'start_date', 'end_date')
