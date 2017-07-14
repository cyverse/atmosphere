from core.models import Project, Instance
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


class ProjectInstanceSerializer(serializers.ModelSerializer):
    project = ProjectRelatedField(queryset=Project.objects.none())
    instance = InstanceRelatedField(source="pk", queryset=Instance.objects.none())
    # Could not fix 'ImproperlyConfiguredError'
    # url = serializers.HyperlinkedIdentityField(
    #     lookup_field="id",
    #     view_name='api:v2:projectinstance-retrieve',
    # )

    class Meta:
        model = Instance
        fields = (
            'id',
            'project',
            'instance'
        )
