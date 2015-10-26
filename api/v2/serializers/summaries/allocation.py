from core.models import Allocation
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class AllocationSummarySerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:allocation-detail',
    )
    class Meta:
        model = Allocation
        fields = ('id', 'uuid', 'url', 'threshold', 'delta')
