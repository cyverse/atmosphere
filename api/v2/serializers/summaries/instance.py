from core.models import Instance
from rest_framework import serializers


class InstanceSummarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Instance
        view_name = 'api_v2:instance-detail'
        fields = ('id', 'url', 'name', 'provider_alias', 'ip_address', 'shell', 'vnc', 'start_date')
