from core.models.quota import Quota
from rest_framework import serializers


class QuotaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Quota
        exclude = ("id",)
