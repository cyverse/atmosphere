from core.models import AccessToken

from rest_framework import serializers


class AccessTokenSerializer(serializers.ModelSerializer):
    issued_time = serializers.DateTimeField(read_only=True, source='token.issuedTime')

    class Meta:
        model = AccessToken
        fields = ('name', 'id', 'issued_time')
