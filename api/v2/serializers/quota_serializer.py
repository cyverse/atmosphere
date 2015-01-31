from core.models import Quota
from rest_framework import serializers


class QuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quota
        # fields = ('id', 'quota')
