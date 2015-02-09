from core.models import ApplicationBookmark as ImageBookmark
from rest_framework import serializers
from .user_serializer import UserSerializer
from .image_summary_serializer import ImageSummarySerializer


class ImageBookmarkSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageSummarySerializer(source='application')
    user = UserSerializer()

    class Meta:
        model = ImageBookmark
        view_name = 'api_v2:applicationbookmark-detail'
        fields = ('id', 'url', 'image', 'user')
