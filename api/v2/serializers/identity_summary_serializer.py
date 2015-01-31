from core.models import Identity
from rest_framework import serializers


class IdentitySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Identity
        fields = ('id',)
