from core.models.project import Project, Group
from core.query import only_current, only_current_source
from rest_framework import serializers
from .instance_serializer import InstanceSerializer
from .volume_serializer import VolumeSerializer
from .get_context_user import get_context_user


class ProjectSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='uuid')
    # Edits to Writable fields..
    owner = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Group.objects.all())
    # These fields are READ-ONLY!
    instances = serializers.SerializerMethodField('get_user_instances')
    volumes = serializers.SerializerMethodField('get_user_volumes')

    def get_user_instances(self, project):
        return [InstanceSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            project.instances.filter(only_current(),
                                     source__provider__active=True
                                     )]

    def get_user_volumes(self, project):
        return [VolumeSerializer(
            item,
            context={'request': self.context.get('request')}).data for item in
            project.volumes.filter(only_current_source(),
                                   instance_source__provider__active=True)]

    def __init__(self, *args, **kwargs):
        user = get_context_user(self, kwargs)
        super(ProjectSerializer, self).__init__(*args, **kwargs)

    class Meta:
        model = Project
        exclude = ('uuid', 'applications')
