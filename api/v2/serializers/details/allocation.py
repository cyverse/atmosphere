from core.models import Allocation
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class AllocationSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:allocation-detail',
    )

    def validate_delta(self, value):
        return self._is_positive_int('delta', value)

    def validate_threshold(self, value):
        return self._is_positive_int('threshold', value)

    def _is_positive_int(self, key, value):
        if type(value) != int or value < 1:
            raise serializers.ValidationError(
                "Value of %s should be >= 1" % key)
        return value

    class Meta:
        model = Allocation
        fields = ('id', 'uuid', 'url', 'threshold', 'delta')
