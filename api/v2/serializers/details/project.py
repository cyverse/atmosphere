from core.models import Project, Group
from rest_framework import serializers
from api.v2.serializers.summaries import (
    InstanceSummarySerializer, VolumeSummarySerializer,
    ImageSummarySerializer, ExternalLinkSummarySerializer,
    GroupSummarySerializer, UserSummarySerializer
)
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField



class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    images = ImageSummarySerializer(
            source='applications', many=True, read_only=True)
    instances = InstanceSummarySerializer(
            source='active_instances', many=True, read_only=True)
    links = ExternalLinkSummarySerializer(
            many=True, read_only=True)
    volumes = VolumeSummarySerializer(
            source='active_volumes', many=True, read_only=True)
    # note: both of these requests become a single DB query, but I'm choosing
    # the owner.name route so the API doesn't break when we start adding users
    # to groups owner = UserSerializer(source='owner.user_set.first')
    owner = ModelRelatedField(
        lookup_field="name",
        queryset=Group.objects.all(),
        serializer_class=GroupSummarySerializer,
        style={'base_template': 'input.html'})
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:project-detail',
    )
    users = UserSummarySerializer(source='get_users', many=True, read_only=True)
    leaders = UserSummarySerializer(source='get_leaders', many=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'description',
            'owner',
            'users',
            'leaders',
            'instances',
            'images',
            'links',
            'volumes',
            'start_date',
            'end_date'
        )
