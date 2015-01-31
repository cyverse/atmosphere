from core.models import Application as Image
from rest_framework import serializers
from .user_serializer import UserSerializer
from .tag_serializer import TagSerializer


class ImageSerializer(serializers.ModelSerializer):
    # todo: add created by field w/ user
    # todo: add tags
    created_by = UserSerializer()
    tags = TagSerializer(many=True)

    class Meta:
        model = Image
        fields = ('id', 'uuid', 'name', 'description', 'icon', 'start_date', 'created_by', 'tags')
