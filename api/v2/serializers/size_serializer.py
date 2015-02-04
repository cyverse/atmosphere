from core.models import Size
from rest_framework import serializers
from .provider_summary_serializer import ProviderSummarySerializer


class SizeSerializer(serializers.ModelSerializer):
    provider = ProviderSummarySerializer()

    class Meta:
        model = Size
        # fields = ('id', 'name', 'description', 'public', 'active', 'start_date', 'end_date', )
