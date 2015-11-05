from core.models.status_type import StatusType
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class StatusTypeSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:statustype-detail',
    )

    class Meta:
        model = StatusType
        fields = (
            'id',
            'url',
            'uuid',
            'name',
            'description',
            'start_date',
            'end_date'
        )
