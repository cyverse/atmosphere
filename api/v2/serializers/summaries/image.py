from core.models import Application as Image
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ImageSummarySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        source='created_by',
        read_only=True)
    tags = serializers.SerializerMethodField()

    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:application-detail',
    )

    def get_tags(self, obj):
        from api.v2.serializers.details import TagSerializer
        serializer = TagSerializer(obj.tags.all(), many=True, context=self.context)
        return serializer.data

    class Meta:
        model = Image
        fields = ('id', 'url', 'uuid', 'name', 'description', 'icon',
                  'tags', 'start_date', 'end_date', 'user')
