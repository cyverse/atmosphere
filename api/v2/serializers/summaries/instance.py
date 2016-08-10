from core.models import Instance, Application as Image
from rest_framework import serializers
from .identity import IdentitySummarySerializer
from .size import SizeSummarySerializer
from .image import ImageSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class InstanceSummarySerializer(serializers.HyperlinkedModelSerializer):
    identity = IdentitySummarySerializer(source='created_by_identity')
    user = serializers.PrimaryKeyRelatedField(
        source='created_by',
        read_only=True)
    provider = serializers.PrimaryKeyRelatedField(
        source='created_by_identity.provider',
        read_only=True)
    status = serializers.CharField(source='esh_status', read_only=True)
    size = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    uuid = serializers.CharField(source='provider_alias')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:instance-detail',
        uuid_field='provider_alias'
    )

    def get_size(self, obj):
        size = obj.get_size()
        serializer = SizeSummarySerializer(size, context=self.context)
        return serializer.data

    def get_image(self, obj):
        image_uuid = obj.application_uuid()
        image = Image.objects.get(uuid=image_uuid)
        serializer = ImageSummarySerializer(image, context=self.context)
        return serializer.data

    class Meta:
        model = Instance
        view_name = 'api:v2:instance-detail'
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'status',
            'size',
            'ip_address',
            'shell',
            'vnc',
            'web_desktop',
            'identity',
            'user',
            'provider',
            'image',
            'start_date',
            'end_date',
        )


class InstanceSuperSummarySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        source='created_by',
        read_only=True)
    provider = serializers.PrimaryKeyRelatedField(
        source='created_by_identity.provider',
        read_only=True)
    status = serializers.CharField(source='esh_status', read_only=True)
    uuid = serializers.CharField(source='provider_alias')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:instance-detail',
        uuid_field='provider_alias'
    )
    class Meta:
        model = Instance
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'status',
            'ip_address',
            'shell',
            'vnc',
            'user',
            'provider',
            'start_date',
            'end_date',
        )
