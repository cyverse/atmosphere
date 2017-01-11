from django_cyverse_auth.models import Token

from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer


class TokenSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSummarySerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:token-detail',
        lookup_field='key'
    )

    class Meta:
        model = Token
        fields = ('key', 'url', 'user', 'api_server_url', 'remote_ip',
                  'issuer', 'issuedTime', 'expireTime')
