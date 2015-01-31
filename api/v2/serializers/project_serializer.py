from core.models import Project
from rest_framework import serializers
from .instance_summary_serializer import InstanceSummarySerializer
from .volume_summary_serializer import VolumeSummarySerializer


class ProjectSerializer(serializers.ModelSerializer):
    instances = InstanceSummarySerializer(many=True)
    volumes = VolumeSummarySerializer(many=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'start_date', 'instances', 'volumes')
