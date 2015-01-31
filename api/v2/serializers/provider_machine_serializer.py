from core.models import ProviderMachine
from rest_framework import serializers
from .image_summary_serializer import ImageSummarySerializer
from .provider_summary_serializer import ProviderSummarySerializer
from .user_serializer import UserSerializer


class ProviderMachineSerializer(serializers.ModelSerializer):
    image = ImageSummarySerializer(source='application')
    provider = ProviderSummarySerializer()
    created_by = UserSerializer()

    class Meta:
        model = ProviderMachine
        fields = ('id', 'image', 'provider', 'created_by', 'start_date', 'end_date')
