from core.models import Project
from rest_framework import serializers
from ..summaries import ProjectSummarySerializer, InstanceSummarySerializer


class ProjectInstanceSerializer(serializers.HyperlinkedModelSerializer):
    project = ProjectSummarySerializer()
    instance = InstanceSummarySerializer()

    class Meta:
        model = Project
        view_name = 'api_v2:project-detail'
        fields = (
            'id',
            'url',
            'project',
            'instance'
        )
