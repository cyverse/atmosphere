from core.models import Identity
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class IdentitySummarySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(read_only=True)
    provider = serializers.PrimaryKeyRelatedField(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:identity-detail',
    )
    class Meta:
        model = Identity
        fields = (
            'id',
            'uuid',
            'url',
            'provider',
        )
