from core.models import ApplicationPatternMatch, Application as Image, PatternMatch
from rest_framework import serializers
from api.v2.serializers.summaries import ImageSummarySerializer, PatternMatchSummarySerializer
from api.v2.serializers.fields import (
    ModelRelatedField,
    filter_current_user_queryset
)


class ImageRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Image.objects.all()

    def to_representation(self, value):
        volume = Image.objects.get(pk=value.pk)
        serializer = ImageSummarySerializer(volume, context=self.context)
        return serializer.data


class ImageAccessListSerializer(serializers.HyperlinkedModelSerializer):
    image = ImageRelatedField(
        source='application',
        queryset=Image.objects.none())
    match = ModelRelatedField(
        source='patternmatch',
        queryset=filter_current_user_queryset,
        serializer_class=PatternMatchSummarySerializer,
        style={'base_template': 'input.html'})
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:applicationaccesslist-detail',
    )

    class Meta:
        model = ApplicationPatternMatch
        fields = (
            'id',
            'url',
            'image',
            'match'
        )
