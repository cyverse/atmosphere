from core.models import Group as Membership
from rest_framework import serializers


class MembershipSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Membership
        view_name = 'api:v2:group-detail'
        fields = ('id', 'url', 'name',)
