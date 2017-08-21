from core.models import Project, Volume
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
    volume = VolumeRelatedField(source="pk", queryset=Volume.objects.none())
    # Could not fix 'ImproperlyConfiguredError'
    # url = serializers.HyperlinkedIdentityField(
    #     view_name='api:v2:projectvolume-detail',
    # )

    class Meta:
        model = Volume
        fields = (
            'id',
            'project',
            'volume'
        )

    def create(self, validated_data):
        validated_data['pk'].project = validated_data['project']
        validated_data['pk'].save()
        return validated_data
