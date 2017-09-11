from core.models import Application as Image, BootScript
from core.metrics.application import _get_summarized_application_metrics
from rest_framework import serializers
from dateutil import rrule
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
    is_featured = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    def get_is_featured(self, application):
        return application.featured()

    def get_metrics(self, application):
        request = self.context.get('request', None)
        user = self.context.get('user', request.user)
        if not user:
            raise Exception("This serializer expects 'user' or an authenticated 'request' including 'user' to be passed in via serializer context! context={'user':user}")
        # Time-series metrics example
        # if not user.is_staff:
        #     return {}
        # interval = rrule.MONTHLY
        # limit = 120
        # if request and 'interval' in request.query_params:
        #     interval_str = request.query_params.get('interval', '').lower()
        #     if 'week' in interval_str:
        #         interval = rrule.WEEKLY
        #     elif 'day' in interval_str or 'daily' in interval_str:
        #         interval = rrule.DAILY
        # return _get_application_metrics(application, interval=interval, day_limit=limit, read_only=True)
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
