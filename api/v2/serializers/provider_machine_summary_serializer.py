from core.models import ProviderMachine
from rest_framework import serializers


class ProviderMachineSummarySerializer(serializers.ModelSerializer):

    class Meta:
        model = ProviderMachine
        fields = ('id', 'start_date', 'end_date')
