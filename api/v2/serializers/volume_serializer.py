from core.models import Volume
from rest_framework import serializers
from .provider_serializer import ProviderSerializer


class VolumeSerializer(serializers.ModelSerializer):
    provider = ProviderSerializer()

    class Meta:
        model = Volume
        fields = ('id', 'size', 'name', 'start_date', 'provider')
