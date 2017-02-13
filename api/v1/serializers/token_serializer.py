from django_cyverse_auth.models import Token
from rest_framework import serializers


class TokenSerializer(serializers.ModelSerializer):
    token = serializers.CharField(read_only=True, source='key')
    username = serializers.CharField(read_only=True, source='user.username')
    expires = serializers.CharField(read_only=True, source='get_expired_time')

    class Meta:
        model = Token
        fields = ('token', 'username', 'expires')
