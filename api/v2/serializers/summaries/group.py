from core.models import Group
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class GroupSummarySerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:group-detail',
    )
    class Meta:
        model = Group
        fields = (
            'id',
            'uuid',
            'url',
            'name',
        )
