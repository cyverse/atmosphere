from core.models import ProjectExternalLink, Project, ExternalLink
from rest_framework import serializers
from api.v2.serializers.summaries import ProjectSummarySerializer
from .link import ExternalLinkSerializer


class ProjectRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return Project.objects.all()

    def to_representation(self, value):
        project = Project.objects.get(pk=value.pk)
        serializer = ProjectSummarySerializer(project, context=self.context)
        return serializer.data


class ExternalLinkRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return ExternalLink.objects.all()

    def to_representation(self, value):
        link = ExternalLink.objects.get(pk=value.pk)
        serializer = ExternalLinkSerializer(link, context=self.context)
        return serializer.data


class ProjectExternalLinkSerializer(serializers.HyperlinkedModelSerializer):
    project = ProjectRelatedField(queryset=Project.objects.none())
    link = ExternalLinkRelatedField(queryset=ExternalLink.objects.none())
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:projectlink-detail',
    )
    class Meta:
        model = ProjectExternalLink
        fields = (
            'id',
            'url',
            'project',
            'link'
        )
