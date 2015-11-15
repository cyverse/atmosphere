from core.models import Application as Image
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ImageSummarySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        source='created_by',
        read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:application-detail',
    )
    class Meta:
        model = Image
        fields = ('id', 'url', 'uuid', 'name', 'description', 'icon',
                  'start_date', 'end_date', 'user')
