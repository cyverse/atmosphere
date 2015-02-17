from core.models.allocation_strategy import Allocation
from rest_framework import serializers


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
