from core.models import Allocation
from rest_framework import serializers


class AllocationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Allocation
        view_name = 'api_v2:allocation-detail'
        # fields = ('id', 'quota')
