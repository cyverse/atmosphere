from core.models import InstanceAction
from rest_framework import serializers


class InstanceActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstanceAction
        # fields = ('id', 'name', 'description')
