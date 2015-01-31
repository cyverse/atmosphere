from core.models import VolumeAction
from rest_framework import serializers


class VolumeActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolumeAction
        # fields = ('id', 'name', 'description')
