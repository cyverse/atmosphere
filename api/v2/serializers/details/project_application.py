from core.models import ProjectApplication, Project, Application
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.summaries import (
    ProjectSummarySerializer, ImageSummarySerializer)


class ProjectApplicationSerializer(serializers.HyperlinkedModelSerializer):
    project = ModelRelatedField(
        queryset=Project.objects.all(),
        serializer_class=ProjectSummarySerializer,
        style={'base_template': 'input.html'})
    image = ModelRelatedField(
        queryset=Application.objects.all(),
        serializer_class=ImageSummarySerializer,
        style={'base_template': 'input.html'},
        source='application')
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:projectapplication-detail',
    )

    class Meta:
        model = ProjectApplication
        validators = [
            # TODO: Fix that 'application' leaks into real-world here.
            UniqueTogetherValidator(
                queryset=ProjectApplication.objects.all(),
                fields=('project', 'application')
                ),
        ]
        fields = (
            'id',
            'url',
            'project',
            'image'
        )
