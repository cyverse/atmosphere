from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.models import ProjectMembership
from core.models import Project
from core.models import Group

from api.v2.serializers.summaries import (
    ProjectSummarySerializer, GroupSummarySerializer)
from api.v2.serializers.fields.base import ModelRelatedField


class ProjectMembershipSerializer(serializers.HyperlinkedModelSerializer):
    project = ModelRelatedField(
        queryset=Project.objects.all(),
        serializer_class=ProjectSummarySerializer,
        style={'base_template': 'input.html'},
        lookup_field='uuid',
        required=False)
    group = ModelRelatedField(
        queryset=Group.objects.all(),
        serializer_class=GroupSummarySerializer,
        style={'base_template': 'input.html'},
        lookup_field='uuid',
        required=False)
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:imageversion_membership-detail',
    )

    class Meta:
        model = ProjectMembership
        validators = [
            UniqueTogetherValidator(
                queryset=ProjectMembership.objects.all(),
                fields=('project', 'group')
            )
        ]
        fields = (
            'id',
            'url',
            'project',
            'group'
        )
