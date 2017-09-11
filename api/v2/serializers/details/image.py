from core.models import Application as Image, BootScript, PatternMatch
from rest_framework import serializers

from api.v2.serializers.summaries import UserSummarySerializer, PatternMatchSummarySerializer
from api.v2.serializers.fields import (
    ModelRelatedField,
    ImageVersionRelatedField,
    TagRelatedField
)
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


def filter_current_user_queryset(modelRelatedField):
    """
    This handy method will allow you to limit the choices of ModelRelatedField
    based on the current request user.


    """
    if 'request' in modelRelatedField.context:
        user = modelRelatedField.context['request'].user
    if 'user' in modelRelatedField.context:
        user = modelRelatedField.context['user']
    # Built for PatternMatch but could be used by any Model that has a `.created_by`
    CoreModel = modelRelatedField.serializer_class.Meta.model
    return CoreModel.objects.filter(created_by=user)


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    created_by = UserSummarySerializer(read_only=True)
    access_list = ModelRelatedField(
        many=True,
        queryset=filter_current_user_queryset,
        serializer_class=PatternMatchSummarySerializer,
        style={'base_template': 'input.html'})
    tags = TagRelatedField(many=True)
    versions = ImageVersionRelatedField(many=True)
    icon = serializers.CharField(source="get_icon_url", read_only=True)
    is_public = SwapBooleanField(source='private')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:application-detail',
    )
    metrics_url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:applicationmetric-detail',
    )

    class Meta:
        model = Image
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            # Adtl. Fields
            'metrics_url',
            'created_by',
            'description',
            'end_date',
            'is_public',
            'icon',
            'start_date',
            'access_list',
            'tags',
            'versions'
        )
