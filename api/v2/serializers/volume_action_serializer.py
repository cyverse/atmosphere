from core.models import VolumeAction
from rest_framework import serializers


class VolumeActionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = VolumeAction
        view_name = 'api_v2:volumeaction-detail'
        # fields = ('id', 'name', 'description')
