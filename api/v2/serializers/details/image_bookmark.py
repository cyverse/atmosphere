from core.models import ApplicationBookmark as ImageBookmark
from rest_framework import serializers
from ..summaries import UserSummarySerializer, ImageSummarySerializer


class ImageBookmarkSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageSummarySerializer(source='application')
    user = UserSummarySerializer()

    class Meta:
        model = ImageBookmark
        view_name = 'api_v2:applicationbookmark-detail'
        fields = ('id', 'url', 'image', 'user')
