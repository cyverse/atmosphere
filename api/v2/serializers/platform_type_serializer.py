from core.models import PlatformType
from rest_framework import serializers


class PlatformTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PlatformType
        view_name = 'api_v2:platformtype-detail'
        fields = ('id', 'url', 'name', 'start_date', 'end_date')