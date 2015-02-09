from core.models import Application as Image
from rest_framework import serializers
from .image_summary_serializer import ImageSummarySerializer
from .tag_serializer import TagSerializer


class ImageTagSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageSummarySerializer(source='application')
    tag = TagSerializer()

    class Meta:
        model = Image
        view_name = 'api_v2:applicationtag-detail'
        fields = ('id', 'url', 'image', 'tag', 'start_date', 'end_date')
