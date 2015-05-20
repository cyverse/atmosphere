from core.models import ProjectInstance, Project, Instance
from rest_framework import serializers
from api.v2.serializers.summaries import ProjectSummarySerializer
from .instance import InstanceSerializer


class ProjectRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Project.objects.all()

    def to_representation(self, value):
        project = Project.objects.get(pk=value.pk)
        serializer = ProjectSummarySerializer(project, context=self.context)
        return serializer.data


class InstanceRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Instance.objects.all()

    def to_representation(self, value):
        instance = Instance.objects.get(pk=value.pk)
        serializer = InstanceSerializer(instance, context=self.context)
        return serializer.data


class ProjectInstanceSerializer(serializers.HyperlinkedModelSerializer):
    project = ProjectRelatedField(queryset=Project.objects.none())
    instance = InstanceRelatedField(queryset=Instance.objects.none())

    class Meta:
        model = ProjectInstance
        view_name = 'api_v2:projectinstance-detail'
        fields = (
            'id',
            'url',
            'project',
            'instance'
        )
