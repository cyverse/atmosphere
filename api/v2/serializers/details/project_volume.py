from core.models import Project
from rest_framework import serializers
from ..summaries import ProjectSummarySerializer, VolumeSummarySerializer


class ProjectVolumeSerializer(serializers.HyperlinkedModelSerializer):
    project = ProjectSummarySerializer()
    volume = VolumeSummarySerializer()

    class Meta:
        model = Project
        view_name = 'api_v2:project-detail'
        fields = (
            'id',
            'url',
            'project',
            'volume'
        )
