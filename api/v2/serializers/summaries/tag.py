from core.models import Tag
from rest_framework import serializers


class TagSummarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Tag
        view_name = 'api:v2:tag-detail'
        fields = ('id', 'url', 'name', 'description')
