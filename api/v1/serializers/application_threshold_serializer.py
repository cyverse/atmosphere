from core.models.application import ApplicationThreshold
from rest_framework import serializers


class ApplicationThresholdSerializer(serializers.ModelSerializer):

    """
    """
    min_ram = serializers.IntegerField(source="memory_min")
    min_disk = serializers.IntegerField(source="storage_min")

    class Meta:
        model = ApplicationThreshold
        exclude = ('id', 'application', 'memory_min', 'storage_min')
