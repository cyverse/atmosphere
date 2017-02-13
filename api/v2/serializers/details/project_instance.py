from core.models import ProjectInstance, Project, Instance
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
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
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:projectinstance-detail',
    )

    class Meta:
        model = ProjectInstance
        validators = [
            UniqueTogetherValidator(
                queryset=ProjectInstance.objects.all(),
                fields=('project', 'instance')
                ),
        ]
        fields = (
            'id',
            'url',
            'project',
            'instance'
        )
