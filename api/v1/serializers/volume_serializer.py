from core.models.volume import Volume
from rest_framework import serializers
from .cleaned_identity_serializer import CleanedIdentitySerializer
from .projects_field import ProjectsField
from .get_context_user import get_context_user


class VolumeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True, source='get_status')
    attach_data = serializers.ReadOnlyField(source='esh_attach_data')
    mount_location = serializers.ReadOnlyField()
    created_by = serializers.ReadOnlyField(
        source="instance_source.created_by.username")
    provider = serializers.ReadOnlyField(
        source="instance_source.provider.uuid")
    identity = CleanedIdentitySerializer(
        source="instance_source.created_by_identity")
    alias = serializers.ReadOnlyField(source='instance_source.identifier')
    start_date = serializers.ReadOnlyField(source='instance_source.start_date')
    end_date = serializers.ReadOnlyField(source='instance_source.end_date')
    projects = ProjectsField()

    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        self.request_user = user
        super(VolumeSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Volume
        exclude = ("instance_source",)
