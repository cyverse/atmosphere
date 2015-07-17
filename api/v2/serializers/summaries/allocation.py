from core.models import Allocation
from rest_framework import serializers


class AllocationSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Allocation
        view_name = 'api:v2:allocation-detail'
        fields = ('id', 'url', 'threshold', 'delta')
