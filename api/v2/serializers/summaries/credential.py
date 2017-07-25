from core.models import Credential
from rest_framework import serializers


class CredentialSummarySerializer(serializers.ModelSerializer):

    class Meta:
        model = Credential
        fields = (
            'id', 'key', 'clean_value',
        )
