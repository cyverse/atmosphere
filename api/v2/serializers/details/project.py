from core.models import Project
from rest_framework import serializers
from api.v2.serializers.summaries import InstanceSummarySerializer,\
    VolumeSummarySerializer, ImageSummarySerializer, ExternalLinkSummarySerializer
from api.v2.serializers.fields import UserRelatedField
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
    owner = UserRelatedField(source='owner.name')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:project-detail',
    )

    class Meta:
        model = Project
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'description',
            'owner',
            'instances',
            'images',
            'links',
            'volumes',
            'start_date',
            'end_date'
        )
