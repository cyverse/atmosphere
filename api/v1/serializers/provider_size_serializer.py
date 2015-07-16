from core.models.size import Size
from rest_framework import serializers


class ProviderSizeSerializer(serializers.ModelSerializer):
    occupancy = serializers.CharField(read_only=True, source='esh_occupancy')
    total = serializers.CharField(read_only=True, source='esh_total')
    remaining = serializers.CharField(read_only=True, source='esh_remaining')
    active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Size
        exclude = ('id', 'start_date', 'end_date')
