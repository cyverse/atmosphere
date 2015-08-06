from core.models import Tag
from rest_framework import serializers
from api.v2.serializers.summaries import TagSummarySerializer


class TagRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(TagRelatedField, self).__init__(**kwargs)

    def to_representation(self, value):
        serializer = TagSummarySerializer(value, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        tag = Tag.objects.get(id=data)
        return tag
