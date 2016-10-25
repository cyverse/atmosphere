from core.models import ProjectVolume, Project, Volume
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from api.v2.serializers.summaries import ProjectSummarySerializer
from .volume import VolumeSerializer


class ProjectRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Project.objects.all()

    def to_representation(self, value):
        project = Project.objects.get(pk=value.pk)
        serializer = ProjectSummarySerializer(project, context=self.context)
        return serializer.data


class VolumeRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Volume.objects.all()

    def to_representation(self, value):
        instance = Volume.objects.get(pk=value.pk)
        serializer = VolumeSerializer(instance, context=self.context)
        return serializer.data


class ProjectVolumeSerializer(serializers.HyperlinkedModelSerializer):
    project = ProjectRelatedField(queryset=Project.objects.none())
    volume = VolumeRelatedField(queryset=Volume.objects.none())
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:projectvolume-detail',
    )

    class Meta:
        model = ProjectVolume
        validators = [
            UniqueTogetherValidator(
                queryset=ProjectVolume.objects.all(),
                fields=('project', 'volume')
                ),
        ]
        fields = (
            'id',
            'url',
            'project',
            'volume'
        )
