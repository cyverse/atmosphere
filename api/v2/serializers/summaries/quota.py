from core.models import Quota
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class QuotaSummarySerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:quota-detail',
    )
    class Meta:
        model = Quota
        fields = (
            'id', 'uuid', 'url',
            #general
            'cpu', 'memory', 'storage',
            # compute
            'instance_count',
            # volume
            'snapshot_count', 'storage_count',
            # networking
            'floating_ip_count', 'port_count',
            )
