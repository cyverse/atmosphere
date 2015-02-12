from core.models import ProviderMachine
from rest_framework import serializers
from .image_summary_serializer import ImageSummarySerializer
from .provider import ProviderSummarySerializer
from .user_serializer import UserSerializer


class ProviderMachineSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageSummarySerializer(source='application')
    provider = ProviderSummarySerializer()
    created_by = UserSerializer()

    class Meta:
        model = ProviderMachine
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'url', 'image', 'provider', 'created_by', 'start_date', 'end_date')


class ProviderMachineSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ProviderMachine
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'url', 'start_date', 'end_date')
