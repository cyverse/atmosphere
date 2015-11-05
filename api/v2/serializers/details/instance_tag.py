from core.models import InstanceTag, Instance, Tag
from rest_framework import serializers
from api.v2.serializers.summaries import InstanceSuperSummarySerializer
from .tag import TagSerializer


class InstanceRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Instance.objects.all()

    def to_representation(self, value):
        instance = Instance.objects.get(pk=value.pk)
        # important! We have to use the SuperSummary because there are non-end_dated
        # instances that don't have a valid size (size='Unknown')
        serializer = InstanceSuperSummarySerializer(
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
