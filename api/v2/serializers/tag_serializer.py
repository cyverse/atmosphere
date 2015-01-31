from core.models import Tag
from rest_framework import serializers
from .user_serializer import UserSerializer


class TagSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Tag
        fields = ('id', 'name', 'description', 'user')
