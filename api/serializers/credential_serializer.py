from core.models.credential import Credential
from rest_framework import serializers


class CredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credential
        exclude = ('identity',)