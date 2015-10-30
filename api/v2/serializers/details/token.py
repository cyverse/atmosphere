from iplantauth.models import Token

from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class TokenSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSummarySerializer(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:token-detail',
        uuid_field='key'
    )
    lookup_field="key"

    class Meta:
        model = Token
        fields = ('key', 'url', 'user', 'api_server_url', 'remote_ip',
                  'issuer', 'issuedTime', 'expireTime')
