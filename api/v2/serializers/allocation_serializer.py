from core.models import Allocation
from rest_framework import serializers


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        # fields = ('id', 'quota')
