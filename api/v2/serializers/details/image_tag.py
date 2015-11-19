from core.models import ApplicationTag as ImageTag, Application as Image, Tag
from rest_framework import serializers
from api.v2.serializers.summaries import ImageSummarySerializer
from .tag import TagSerializer


class ImageRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Image.objects.all()

    def to_representation(self, value):
        volume = Image.objects.get(pk=value.pk)
        serializer = ImageSummarySerializer(volume, context=self.context)
        return serializer.data


class TagRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Tag.objects.all()

    def to_representation(self, value):
        tag = Tag.objects.get(pk=value.pk)
        serializer = TagSerializer(tag, context=self.context)
        return serializer.data


class ImageTagSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageRelatedField(
        source='application',
        queryset=Image.objects.none())
    tag = TagRelatedField(queryset=Tag.objects.none())
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:applicationtag-detail',
    )
    class Meta:
        model = ImageTag
        fields = (
            'id',
            'url',
            'image',
            'tag'
        )
