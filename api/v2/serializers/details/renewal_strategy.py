from core.models.renewal_strategy import RenewalStrategy
from rest_framework import serializers
from cyverse_allocation.cyverse_rules_engine_setup import renewal_strategies

class RenewalStrategySerializer(serializers.HyperlinkedModelSerializer):

    compute_allowed = serializers.SerializerMethodField()
    renewed_after_days = serializers.SerializerMethodField()

    def get_compute_allowed(self,strategy):
        return renewal_strategies[strategy]['compute_allowed']

    def get_renewed_after_days(self,strategy):
        return renewal_strategies[strategy]['renewed_after_days']

    class Meta:
        model = RenewalStrategy
        fields = (
            'id',
            'name',
            'description',
            'compute_allowed',
            'renewed_after_days'
        )
