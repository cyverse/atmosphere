from core.models import Group as Membership
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class MembershipSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:group-detail',
    )

    class Meta:
        model = Membership
        fields = ('id', 'uuid', 'url', 'name',)
