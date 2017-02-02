from core.models.renewal_strategy import RenewalStrategy
from rest_framework import serializers

class RenewalStrategySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = RenewalStrategy
        fields = (
            'id',
            'name',
            'description',
        )
