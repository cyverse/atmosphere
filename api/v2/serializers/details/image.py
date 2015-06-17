from core.models import Application as Image
from rest_framework import serializers
from api.v2.serializers.summaries import TagSummarySerializer, UserSummarySerializer
from api.v2.serializers.fields import ImageVersionRelatedField


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    created_by = UserSummarySerializer()
    tags = TagSummarySerializer(many=True)
    versions = ImageVersionRelatedField(many=True)
    icon = serializers.CharField(source="get_icon_url", read_only=True)

    class Meta:
        model = Image
        view_name = 'api:v2:application-detail'
        fields = (
            'id', 'url', 'uuid', 'name', 'description', 'icon', 'created_by',
            'private', 'tags', 'start_date', 'end_date', 'versions'
        )
