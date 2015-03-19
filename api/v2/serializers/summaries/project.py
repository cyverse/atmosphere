from core.models import Project
from rest_framework import serializers


class ProjectSummarySerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.StringRelatedField(source='owner.name')

    class Meta:
        model = Project
        view_name = 'api_v2:project-detail'
        fields = (
            'id',
            'url',
            'name',
            'description',
            'owner',
            'start_date',
            'end_date'
        )
