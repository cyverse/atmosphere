from core.models.allocation_strategy import Allocation
from rest_framework import serializers


class AllocationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Allocation


class InstanceSizeInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    identifier = serializers.CharField()
    cpu = serializers.IntegerField()
    disk = serializers.IntegerField()
    ram = serializers.IntegerField()


class InstanceHistoryInputSerializer(serializers.Serializer):
    status = serializers.CharField()
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    size = InstanceSizeInputSerializer()


class InstanceInputSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    machine = serializers.CharField(source="machine.name")
    provider = serializers.CharField(source="provider.name")
    history = InstanceHistoryInputSerializer(many=True)


class RuleInputSerializer(serializers.Serializer):
    name = serializers.CharField()


class CreditInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    increase_date = serializers.CharField()


class AllocationInputSerializer(serializers.Serializer):
    instances = InstanceInputSerializer(many=True)
    rules = RuleInputSerializer(many=True)
    credits = CreditInputSerializer(many=True)
    start_date = serializers.CharField()
    end_date = serializers.CharField()


class HistoryResultSerializer(serializers.Serializer):
    burn_rate = serializers.CharField()
    clock_time = serializers.CharField()
    total_time = serializers.CharField()
    status_name = serializers.CharField()


class InstanceResultSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    history_list = HistoryResultSerializer(many=True)


class TimePeriodSerializer(serializers.Serializer):
    instance_results = InstanceResultSerializer(many=True)
    start_date = serializers.CharField(source="start_counting_date")
    end_date = serializers.CharField(source="stop_counting_date")
    total_credit = serializers.CharField()


class AllocationResultSerializer(serializers.Serializer):
    allocation = AllocationInputSerializer()
    carry_forward = serializers.BooleanField()
    start_date = serializers.CharField(source="window_start")
    end_date = serializers.CharField(source="window_end")
    time_periods = TimePeriodSerializer(many=True)
