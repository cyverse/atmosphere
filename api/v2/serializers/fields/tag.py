from core.models import Tag
from rest_framework import serializers
from api.v2.serializers.summaries import TagSummarySerializer


class TagRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(TagRelatedField, self).__init__(**kwargs)

    def to_representation(self, value):
        username = value.__str__()
        user = Tag.objects.get(username=username)
        serializer = TagSummarySerializer(user, context=self.context)
        return serializer.data
