from core.models import InstanceAction
from rest_framework import serializers


class InstanceActionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = InstanceAction
        view_name = 'api_v2:instanceaction-detail'
        # fields = ('id', 'name', 'description')
