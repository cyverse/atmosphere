from core.models import Application as Image
from rest_framework import serializers


class ImageSummarySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.PrimaryKeyRelatedField(source='created_by', read_only=True)

    class Meta:
        model = Image
        view_name = 'api:v2:application-detail'
        fields = ('id', 'url', 'uuid', 'name', 'description', 'icon',
                  'start_date', 'end_date')
