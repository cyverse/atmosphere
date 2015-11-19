from core.models import Tag
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class TagSummarySerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:tag-detail',
    )
    class Meta:
        model = Tag
        fields = ('id', 'uuid', 'url', 'name', 'description')
