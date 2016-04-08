from rest_framework import serializers

from core.models import InstanceAction


class InstanceActionSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:instanceaction-detail',
    )

    class Meta:
        model = InstanceAction
