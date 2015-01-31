from core.models import Application as Image
from rest_framework import serializers
from .user_serializer import UserSerializer
from .tag_serializer import TagSerializer


class ImageSummarySerializer(serializers.ModelSerializer):

    class Meta:
        model = Image
        fields = ('id', 'uuid', 'name', 'description', 'icon', 'start_date', 'end_date')
