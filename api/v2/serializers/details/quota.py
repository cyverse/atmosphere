from core.models import Allocation
from core.models import Quota

from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class QuotaSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:quota-detail',
    )

    def validate_cpu(self, value):
        return self._is_positive_int('cpu', value)

    def validate_memory(self, value):
        return self._is_positive_int('memory', value)

    def validate_storage(self, value):
        return self._is_positive_int('storage', value)

    def validate_storage_count(self, value):
        return self._is_positive_int('storage_count', value)

    def _is_positive_int(self, key, value):
        if type(value) != int or value < 1:
            raise serializers.ValidationError(
                "Value of %s should be >= 1" % key)
        return value

    class Meta:
        model = Quota
        fields = (
            'id', 'uuid', 'url',
            # general
            'cpu', 'memory', 'storage',
            # compute
            'instance_count',
            # volume
            'snapshot_count', 'storage_count',
            # networking
            'floating_ip_count', 'port_count',
            )


class AllocationSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:allocation-detail',
    )

    def validate_delta(self, value):
        return self._is_integer('delta', value)

    def validate_threshold(self, value):
        return self._is_positive_int('threshold', value)

    def _is_positive_int(self, key, value):
        if type(value) != int or value < 1:
            raise serializers.ValidationError(
                "Value of %s should be >= 1" % key)
        return value

    def _is_integer(self, key, value):
        if type(value) != int:
            raise serializers.ValidationError(
                "Value of %s should be an integer." % key)
        return value

    class Meta:
        model = Allocation
        fields = ('id', 'uuid', 'url', 'threshold', 'delta')
