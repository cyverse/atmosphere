from core.models import Application as Image
from rest_framework import serializers
from .user_serializer import UserSerializer
from .tag_serializer import TagSerializer


class ImageSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Image
        view_name = 'api_v2:application-detail'
        fields = ('id', 'url', 'uuid', 'name', 'description', 'icon', 'start_date', 'end_date')
