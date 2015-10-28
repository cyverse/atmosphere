from core.models import Group
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from api.v2.serializers.summaries import UserSummarySerializer


class MembershipSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:group-detail',
    )
    users = UserSummarySerializer(many=True, source='user_set')
    class Meta:
        model = Group
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'users'
        )
