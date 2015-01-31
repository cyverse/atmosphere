from core.models import PlatformType
from rest_framework import serializers


class PlatformTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformType