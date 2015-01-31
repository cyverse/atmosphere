from core.models.user import AtmosphereUser
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtmosphereUser
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser')
