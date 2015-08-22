from core.models import License, LicenseType
from rest_framework import serializers


class LicenseTypeSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = LicenseType
        fields = ('id', 'name', 'description')
