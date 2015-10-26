from core.models import Project
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ProjectSummarySerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.StringRelatedField(source='owner.name')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:project-detail',
    )
    class Meta:
        model = Project
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            'description',
            'owner',
            'start_date',
            'end_date'
        )
