from core.models import Credential
from rest_framework import serializers
from api.v2.serializers.summaries import IdentitySummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class CredentialSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:credential-detail',
    )
    identity = IdentitySummarySerializer()

    class Meta:
        model = Credential
        fields = ('id', 'uuid', 'url', 'identity', 'key', 'value')

