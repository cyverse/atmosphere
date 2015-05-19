from core.models.status_type import StatusType
from rest_framework import serializers


class StatusTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = StatusType
        view_name = 'api_v2:statustype-detail'
        fields = (
            'id',
            'url',
            'name',
            'description',
            'start_date',
            'end_date'
        )
