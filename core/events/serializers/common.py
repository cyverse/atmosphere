"""
These basic classes are often used while creating EventSerializers
"""

from rest_framework import serializers
from core.models import (
    AtmosphereUser, Instance)


class AtmosphereUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtmosphereUser
        fields = ("username",)


class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instance
        fields = ('provider_alias',)
