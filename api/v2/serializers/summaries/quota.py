from core.models import Quota
from rest_framework import serializers


class QuotaSummarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Quota
        view_name = 'api_v2:quota-detail'
        fields = ('id', 'url', 'cpu', 'memory', 'storage', 'storage_count', 'suspended_count')
