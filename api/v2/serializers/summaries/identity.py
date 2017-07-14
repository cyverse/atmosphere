from core.models import Identity
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class IdentitySummarySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(read_only=True)
    provider = serializers.PrimaryKeyRelatedField(read_only=True)
    key = serializers.SerializerMethodField()
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:identity-detail',
    )

    def get_key(self, identity):
        return identity.get_key()

    class Meta:
        model = Identity
        fields = (
            'id',
            'uuid',
            'url',
            'key',
            'provider',
        )
