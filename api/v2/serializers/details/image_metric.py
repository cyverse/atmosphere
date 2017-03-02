from core.models import Application as Image, BootScript
from core.metrics import get_image_metrics
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


class ImageMetricSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:applicationmetric-detail',
    )
    metrics = serializers.SerializerMethodField()

    def get_metrics(self, application):
        return get_image_metrics(application)

    class Meta:
        model = Image
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            # Adtl. Fields
            'metrics',
        )
