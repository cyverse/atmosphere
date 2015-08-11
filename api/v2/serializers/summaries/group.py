from core.models import Group
from rest_framework import serializers


class GroupSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Group
        view_name = 'api:v2:group-detail'
        fields = (
            'id',
            'url',
            'name',
        )
