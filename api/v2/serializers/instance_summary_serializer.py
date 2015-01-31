from core.models import Instance
from rest_framework import serializers


class InstanceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Instance
        fields = ('id', 'name', 'provider_alias', 'ip_address', 'shell', 'vnc', 'start_date')
