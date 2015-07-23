from core.models import Application as Image
from rest_framework import serializers
from api.v2.serializers.summaries import TagSummarySerializer, UserSummarySerializer
from api.v2.serializers.fields import ImageVersionRelatedField


class SwapBooleanField(serializers.BooleanField):
    def to_internal_value(self, data):
        truth_value = super(SwapBooleanField, self).to_internal_value(data)
        swap_value = not truth_value
        return swap_value

    def to_representation(self, value):
        truth_value = super(SwapBooleanField, self).to_representation(value)
        swap_value = not truth_value
        return swap_value


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    created_by = UserSummarySerializer()
    tags = TagSummarySerializer(many=True)
    versions = ImageVersionRelatedField(many=True)
    icon = serializers.CharField(source="get_icon_url", read_only=True)
    is_public = SwapBooleanField(source='private')

    class Meta:
        model = Image
        view_name = 'api:v2:application-detail'
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            # Adtl. Fields
            'created_by',
            'description',
            'end_date',
            'is_public',
            'icon',
            'start_date',
            'tags',
            'versions'
        )
