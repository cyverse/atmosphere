from core.models import Size
from rest_framework import serializers
from .provider_summary_serializer import ProviderSummarySerializer


class SizeSummarySerializer(serializers.ModelSerializer):

    class Meta:
        model = Size
        fields = ('id', 'alias', 'name', 'cpu', 'disk', 'mem', 'active', 'start_date', 'end_date')
