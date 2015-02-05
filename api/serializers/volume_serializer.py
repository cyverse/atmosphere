from core.models.volume import Volume
from rest_framework import serializers
from .cleaned_identity_serializer import CleanedIdentitySerializer
from .projects_field import ProjectsField
from .get_context_user import get_context_user


class VolumeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True, source='get_status')
    attach_data = serializers.Field(source='esh_attach_data')
    #metadata = serializers.Field(source='esh_metadata')
    mount_location = serializers.Field()
    created_by = serializers.SlugRelatedField(slug_field='username',
                                              read_only=True)
    provider = serializers.Field(source="provider.uuid")
    identity = CleanedIdentitySerializer(source="created_by_identity")
    alias = serializers.Field(source='identifier')
    projects = ProjectsField()

    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        self.request_user = user
        super(VolumeSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Volume
        exclude = ('id', 'created_by_identity', 'end_date')
