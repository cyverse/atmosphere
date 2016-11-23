from core.models import Group
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from api.v2.serializers.summaries import UserSummarySerializer


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:group-detail',
    )
    users = UserSummarySerializer(source='user_set', many=True)
    leaders = UserSummarySerializer(source='get_leaders', many=True, read_only=True)

    class Meta:
        model = Group
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'users',
            'leaders',
        )
