from core.models import LicenseType
from rest_framework import serializers


class LicenseTypeSummarySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = LicenseType
        fields = ('id', 'name', 'description')
