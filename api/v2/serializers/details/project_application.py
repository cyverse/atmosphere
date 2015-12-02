from core.models import ProjectApplication, Project, Application
from rest_framework import serializers
from api.v2.serializers.summaries import ProjectSummarySerializer
from .application import ApplicationSerializer


class ProjectRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Project.objects.all()

    def to_representation(self, value):
        project = Project.objects.get(pk=value.pk)
        serializer = ProjectSummarySerializer(project, context=self.context)
        return serializer.data


class ApplicationRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Application.objects.all()

    def to_representation(self, value):
        application = Application.objects.get(pk=value.pk)
        serializer = ApplicationSerializer(application, context=self.context)
        return serializer.data


class ProjectApplicationSerializer(serializers.HyperlinkedModelSerializer):
    project = ProjectRelatedField(queryset=Project.objects.none())
    application = ApplicationRelatedField(queryset=Application.objects.none())
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:projectapplication-detail',
    )
    class Meta:
        model = ProjectApplication
        fields = (
            'id',
            'url',
            'project',
            'application'
        )
