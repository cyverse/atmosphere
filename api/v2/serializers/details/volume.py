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


class VolumeSerializer(serializers.HyperlinkedModelSerializer):
    description = serializers.CharField(required=False)

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

    uuid = serializers.CharField(source='instance_source.identifier',
                                 read_only=True)

    projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    snapshot_id = serializers.CharField(write_only=True, required=False)
    image_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Volume
        view_name = 'api:v2:volume-detail'
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
        description = validated_data.get('description')
        identifier = validated_data.get("identifier")
        provider = validated_data.get("provider")
        user = validated_data.get("user")
        identity = validated_data.get("identity")
        start_date = validated_data.get("created_on")

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

    def update(self, instance, validated_data):
        if 'instance_source' in validated_data:
            source = instance.instance_source
            source_data = validated_data.pop('instance_source')
            for key, val in source_data.items():
                setattr(source, key, val)
            source.save()
        for (key, val) in validated_data.items():
            setattr(instance, key, val)
        instance.save()
        return instance
