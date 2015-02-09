from core.models import Application as Image
from rest_framework import serializers
from .instance_summary_serializer import InstanceSummarySerializer
from .tag_serializer import TagSerializer


class InstanceTagSerializer(serializers.HyperlinkedModelSerializer):
    instance = InstanceSummarySerializer()
    tag = TagSerializer()

    class Meta:
        model = Image
        view_name = 'api_v2:instancetag-detail'
        fields = ('id', 'url', 'instance', 'tag', 'start_date', 'end_date')
