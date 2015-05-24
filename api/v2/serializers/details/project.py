from core.models import Project
from rest_framework import serializers
from api.v2.serializers.summaries import InstanceSummarySerializer, VolumeSummarySerializer, ImageSummarySerializer
from api.v2.serializers.fields import UserRelatedField


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    instances = InstanceSummarySerializer(source='active_instances',
                                          many=True, read_only=True)
    volumes = VolumeSummarySerializer(source='active_volumes',
                                      many=True, read_only=True)
    images = ImageSummarySerializer(source='applications',
                                    many=True, read_only=True)
    # note: both of these requests become a single DB query, but I'm choosing the
    # owner.name route so the API doesn't break when we start adding users to groups
    # owner = UserSerializer(source='owner.user_set.first')
    owner = UserRelatedField(source='owner.name')

    class Meta:
        model = Project
        view_name = 'api_v2:project-detail'
        fields = (
            'id',
            'url',
            'name',
            'description',
            'owner',
            'instances',
            'volumes',
            'images',
            'start_date',
            'end_date'
        )
