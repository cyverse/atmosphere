from core.models.provider import ProviderType
from rest_framework import serializers


class ProviderTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProviderType
