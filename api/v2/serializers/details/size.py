from core.models import Size
from rest_framework import serializers
from api.v2.serializers.summaries import ProviderSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class SizeSerializer(serializers.HyperlinkedModelSerializer):
    provider = ProviderSummarySerializer()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:size-detail',
    )
    class Meta:
        model = Size
        fields = (
            'id',
            'url',
            'uuid',
            'alias',
            'name',
            'cpu',
            'disk',
            'root',
            'mem',
            'active',
            'provider',
            'start_date',
            'end_date')
