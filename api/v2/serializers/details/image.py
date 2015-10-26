from core.models import Application as Image, BootScript
from rest_framework import serializers

from api.v2.serializers.summaries import UserSummarySerializer
from api.v2.serializers.fields import (
        ImageVersionRelatedField, TagRelatedField)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


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
    created_by = UserSummarySerializer(read_only=True)
    tags = TagRelatedField(many=True)
    versions = ImageVersionRelatedField(many=True)
    icon = serializers.CharField(source="get_icon_url", read_only=True)
    is_public = SwapBooleanField(source='private')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:application-detail',
    )
    class Meta:
        model = Image
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
