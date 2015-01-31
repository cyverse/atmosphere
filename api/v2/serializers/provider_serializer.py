from core.models import Provider
from rest_framework import serializers


class ProviderSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='location')

    class Meta:
        model = Provider
        fields = ('id', 'name', 'description', 'public')
