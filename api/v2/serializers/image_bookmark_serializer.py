from core.models import ApplicationBookmark as ImageBookmark
from rest_framework import serializers
from .user_serializer import UserSerializer
from .image_summary_serializer import ImageSummarySerializer


class ImageBookmarkSerializer(serializers.ModelSerializer):
    image = ImageSummarySerializer(source='application')
    user = UserSerializer()

    class Meta:
        model = ImageBookmark
        fields = ('id', 'image', 'user')
