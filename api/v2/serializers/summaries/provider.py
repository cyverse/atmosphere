from core.models import Provider
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ProviderSummarySerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='location')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:provider-detail',
    )
    class Meta:
        model = Provider
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'description',
            'public',
            'active',
            'start_date',
            'end_date',
        )
