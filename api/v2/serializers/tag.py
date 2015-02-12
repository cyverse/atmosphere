from core.models import Tag
from rest_framework import serializers
from .user import UserSerializer


class TagSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Tag
        view_name = 'api_v2:tag-detail'
        fields = ('id', 'url', 'name', 'description', 'user')
