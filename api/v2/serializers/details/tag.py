from core.models import Tag
from rest_framework import serializers
from ..summaries import UserSummarySerializer


class TagSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = Tag
        view_name = 'api_v2:tag-detail'
        fields = ('id', 'url', 'name', 'description', 'user')
