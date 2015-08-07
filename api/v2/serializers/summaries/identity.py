from core.models import Identity
from rest_framework import serializers


class IdentitySummarySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(read_only=True)
    provider = serializers.PrimaryKeyRelatedField(read_only=True)
    url = serializers.CharField(read_only=True)

    class Meta:
        model = Identity
        view_name = 'api:v2:identity-detail'
        fields = (
            'id',
            'uuid',
            'url',
            'provider',
        )
