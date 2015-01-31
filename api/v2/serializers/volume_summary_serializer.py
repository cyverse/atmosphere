from core.models import Volume
from rest_framework import serializers


class VolumeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = ('id', 'size', 'name', 'start_date', 'provider')
