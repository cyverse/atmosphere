from core.models.maintenance import MaintenanceRecord
from rest_framework import serializers


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    provider_id = serializers.Field(source='provider.uuid')

    class Meta:
        model = MaintenanceRecord
        exclude = ('provider',)