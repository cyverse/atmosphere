from core.models import Volume
from rest_framework import serializers
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.summaries import (
    IdentitySummarySerializer,
    ProviderSummarySerializer,
    UserSummarySerializer
)
from core.models import Identity, Provider
from core.models.instance_source import InstanceSource
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class VolumeSerializer(serializers.HyperlinkedModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True)

    identity = ModelRelatedField(source="instance_source.created_by_identity",
                                 queryset=Identity.objects.all(),
                                 serializer_class=IdentitySummarySerializer,
                                 style={'base_template': 'input.html'})

    provider = ModelRelatedField(source="instance_source.provider",
                                 queryset=Provider.objects.all(),
                                 serializer_class=ProviderSummarySerializer,
                                 style={'base_template': 'input.html'})

    user = UserSummarySerializer(source='instance_source.created_by',
                                 read_only=True)

    projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    snapshot_id = serializers.CharField(write_only=True, allow_blank=True,
                                        required=False)
    image_id = serializers.CharField(write_only=True, allow_blank=True,
                                     required=False)
    uuid = serializers.CharField(source='instance_source.identifier',
                                 read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:volume-detail',
        uuid_field='identifier',
    )
    class Meta:
        model = Volume

        read_only_fields = ("user", "uuid", "start_date", "end_date")
        fields = (
            'id',
            'uuid',
            'name',
            'description',
            'identity',
            'user',
            'provider',
            'projects',
            'size',
            'url',

            'snapshot_id',
            'image_id',

            'start_date',
            'end_date')

    def validate(self, data):
        image_id = data.get('image')
        snapshot_id = data.get('snapshot')

        #: Only allow one at a time
        if snapshot_id and image_id:
            raise serializers.ValidationError(
                "Use either `snapshot_id` or `image_id` not both.")
        return data

    def create(self, validated_data):
        name = validated_data.get('name')
        size = validated_data.get('size')
        identifier = validated_data.get("identifier")
        description = validated_data.get('description')
        user = validated_data.get("user")
        start_date = validated_data.get("created_on")

        instance_source = validated_data.get("instance_source")
        identity = instance_source.get("created_by_identity")
        provider = instance_source.get('provider')

        source = InstanceSource.objects.create(
            identifier=identifier,
            provider=provider,
            created_by=user,
            created_by_identity=identity)

        kwargs = {
            "name": name,
            "size": size,
            "description": description,
            "instance_source": source,
            "start_date": start_date
        }

        return Volume.objects.create(**kwargs)


class UpdateVolumeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)

    class Meta:
        model = Volume
        view_name = 'api:v2:volume-detail'
        fields = ('name', 'description')
