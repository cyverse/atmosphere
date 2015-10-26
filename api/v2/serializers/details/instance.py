from core.models import BootScript, Instance, Application as Image
from rest_framework import serializers
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.summaries import (
    IdentitySummarySerializer,
    UserSummarySerializer,
    ProviderSummarySerializer,
    SizeSummarySerializer,
    ImageSummarySerializer,
    ImageVersionSummarySerializer,
    BootScriptSummarySerializer
)
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    identity = IdentitySummarySerializer(source='created_by_identity')
    user = UserSummarySerializer(source='created_by')
    provider = ProviderSummarySerializer(source='created_by_identity.provider')
    status = serializers.CharField(source='esh_status', read_only=True)
    projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    scripts = ModelRelatedField(
        many=True, required=False,
        queryset=BootScript.objects.all(),
        serializer_class=BootScriptSummarySerializer,
        style={'base_template': 'input.html'})
    size = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
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

    def get_version(self, obj):
        version = obj.source.providermachine.application_version
        serializer = ImageVersionSummarySerializer(
            version,
            context=self.context)
        return serializer.data

    class Meta:
        model = Instance
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
            'version',  # NOTE:Should replace image?
            'scripts',
            'projects',
            'start_date',
            'end_date',
        )
