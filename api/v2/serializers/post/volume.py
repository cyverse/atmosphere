from core.models import (
    InstanceSource, Volume, Identity, Project)
from rest_framework import serializers


class VolumeSerializer(serializers.ModelSerializer):
    """
    This serializer should only be used for Volume Creation.
    This serializer should *never* be returned to the user.
    Instances created from this serializer should be
    re-serialized with a GET/Details Serializer.
    """
    identity = serializers.SlugRelatedField(
        source='created_by_identity', slug_field='uuid',
        queryset=Identity.objects.all())
    name = serializers.CharField()
    project = serializers.SlugRelatedField(
        source="projects", slug_field="uuid", queryset=Project.objects.all(),
        required=False, allow_null=True)
    snapshot_id = serializers.CharField(write_only=True, allow_blank=True,
                                        required=False)
    image_id = serializers.CharField(write_only=True, allow_blank=True,
                                     required=False)

    def create(self, validated_data):
        name = validated_data.get('name')
        size = validated_data.get('size')
        identifier = validated_data.get("identifier")
        description = validated_data.get('description')
        user = validated_data.get("user")
        start_date = validated_data.get("created_on")
        instance_source = validated_data.get("instance_source")
        identity = instance_source.get("created_by_identity")
        provider = identity.provider

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

    def is_valid(self, raise_exception=False):
        data = self.initial_data
        project = data.get('project')
        if type(project) == int:
            if raise_exception:
                raise serializers.ValidationError(
                    "The 'project' argument (%s) should be a UUID, not an Int."
                    % project)
            return False
        return super(VolumeSerializer, self).is_valid(
            raise_exception=raise_exception)

    def validate(self, data):
        image_id = data.get('image_id')
        snapshot_id = data.get('snapshot_id')

        #: Only allow one at a time
        if snapshot_id and image_id:
            raise serializers.ValidationError(
                "Use either `snapshot_id` or `image_id` not both.")
        return data

    class Meta:
        model = Volume
        fields = (
            # Required
            'description',
            'identity',
            'name',
            'size',
            # Optional
            'project',
            # Optional + one or the other
            'image_id',
            'snapshot_id',
        )
