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
    launch_success = serializers.SerializerMethodField()
    launch_failure = serializers.SerializerMethodField()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:application-detail',
    )

    def get_launch_failure(self, application):
        inactive_instance_num = 0
        # TOO SLOW!
        # for prov_machine in application._current_machines():
        #     inactive_instance_num += prov_machine.failed_instances().count()
        return inactive_instance_num

    def get_launch_success(self, application):
        active_instance_num = 0
        # TOO SLOW!
        # for prov_machine in application._current_machines():
        #     active_instance_num += prov_machine.active_instances().count()
        return active_instance_num

    class Meta:
        model = Image
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            # Adtl. Fields
            'launch_success',
            'launch_failure',
            'created_by',
            'description',
            'end_date',
            'is_public',
            'icon',
            'start_date',
            'tags',
            'versions'
        )
