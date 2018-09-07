from core.models import Application as Image
from core.metrics.application import _get_summarized_application_metrics
from rest_framework import serializers
from api.v2.serializers.fields import ImageVersionRelatedField
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
    is_featured = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    def get_is_featured(self, application):
        return application.featured()

    def get_metrics(self, application):
        request = self.context.get('request', None)
        user = self.context.get('user', request.user)
        if not user:
            raise Exception("This serializer expects 'user' or an authenticated 'request' including 'user' to be passed in via serializer context! context={'user':user}")
        # Summarized metrics example
        return _get_summarized_application_metrics(application)

    class Meta:
        model = Image
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            # Adtl. Fields
            'metrics',
            'is_featured',
        )
