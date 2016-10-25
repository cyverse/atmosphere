from core.models import ProjectExternalLink, Project, ExternalLink
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.summaries import (
    ProjectSummarySerializer, ExternalLinkSummarySerializer)

class ProjectExternalLinkSerializer(serializers.HyperlinkedModelSerializer):
    project = ModelRelatedField(
        queryset=Project.objects.all(),
        serializer_class=ProjectSummarySerializer,
        style={'base_template': 'input.html'})
    external_link = ModelRelatedField(
        queryset=ExternalLink.objects.all(),
        serializer_class=ExternalLinkSummarySerializer,
        style={'base_template': 'input.html'},
        source='externallink')
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:projectlinks-detail',
    )

    class Meta:
        model = ProjectExternalLink
        validators = [
            UniqueTogetherValidator(
                queryset=ProjectExternalLink.objects.all(),
                fields=('project', 'externallink')
                ),
        ]
        fields = (
            'id',
            'url',
            'project',
            'external_link'
        )
