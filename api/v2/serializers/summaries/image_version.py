from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ImageVersionSummarySerializer(serializers.HyperlinkedModelSerializer):
    # Required when its a uuid -- otherwise LONGINT
    id = serializers.CharField(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:imageversion-detail',
        uuid_field='id'
    )

    class Meta:
        model = ImageVersion
        fields = ('id', 'url', 'name')
