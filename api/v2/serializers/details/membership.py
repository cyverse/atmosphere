from core.models import Group as Membership
from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer


class MembershipSerializer(serializers.HyperlinkedModelSerializer):
    leaders = UserSummarySerializer(many=True)

    class Meta:
        model = Membership
        view_name = 'api:v2:group-detail'
        fields = ('id', 'url', 'name','leaders')
