from core.models import InstanceTag, Instance, Tag
from rest_framework import serializers
from api.v2.serializers.summaries import InstanceSummarySerializer
from .tag import TagSerializer


class InstanceRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Instance.objects.all()

    def to_representation(self, value):
        instance = Instance.objects.get(pk=value.pk)
        serializer = InstanceSummarySerializer(
            instance,
            context=self.context)
        return serializer.data


class TagRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Tag.objects.all()

    def to_representation(self, value):
        tag = Tag.objects.get(pk=value.pk)
        serializer = TagSerializer(tag, context=self.context)
        return serializer.data


class InstanceTagSerializer(serializers.HyperlinkedModelSerializer):
    instance = InstanceRelatedField(queryset=Instance.objects.none())
    tag = TagRelatedField(queryset=Tag.objects.none())
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:instancetag-detail',
    )
    class Meta:
        model = InstanceTag
        fields = (
            'id',
            'url',
            'instance',
            'tag'
        )
