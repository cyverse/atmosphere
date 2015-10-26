from core.models import Quota
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class QuotaSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:quota-detail',
    )

    class Meta:
        model = Quota
        fields = (
            'id',
            'uuid',
            'url',
            'cpu',
            'memory',
            'storage',
            'storage_count',
            'suspended_count')
