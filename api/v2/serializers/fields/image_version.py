from rest_framework import serializers
from api.v2.serializers.summaries import ImageVersionSummarySerializer


class ImageVersionRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(ImageVersionRelatedField, self).__init__(**kwargs)

    def to_representation(self, value):
        serializer = ImageVersionSummarySerializer(value, context=self.context)
        return serializer.data
