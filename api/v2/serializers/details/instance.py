from core.models import Instance, Size, Application as Image
from rest_framework import serializers
from api.v2.serializers.summaries import (
    IdentitySummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    SizeSummarySerializer,
    ImageSummarySerializer,
    ImageVersionSummarySerializer
)


class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    identity = IdentitySummarySerializer(source='created_by_identity')
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer(source='created_by_identity.provider')
    status = serializers.CharField(source='esh_status', read_only=True)
    projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    size = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
    uuid = serializers.CharField(source='provider_alias')

    def get_size(self, obj):
        size_alias = obj.esh_size()
        provider_id = obj.created_by_identity.provider_id
        size = Size.objects.get(alias=size_alias, provider=provider_id)
        serializer = SizeSummarySerializer(size, context=self.context)
        return serializer.data

    def get_image(self, obj):
        image_uuid = obj.application_uuid()
        image = Image.objects.get(uuid=image_uuid)
        serializer = ImageSummarySerializer(image, context=self.context)
        return serializer.data

    def get_version(self, obj):
        version = obj.source.providermachine.application_version
        serializer = ImageVersionSummarySerializer(version, context=self.context)
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
            'identity',
            'user',
            'provider',
            'image',
            'version', #NOTE:Should replace image?
            'projects',
            'start_date',
            'end_date',
        )
