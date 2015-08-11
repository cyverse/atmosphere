from core.models import License, LicenseType
from rest_framework import serializers


class LicenseSummarySerializer(serializers.HyperlinkedModelSerializer):
    type = serializers.SlugRelatedField(
        source='license_type',
        slug_field='name',
        queryset=LicenseType.objects.all())

    class Meta:
        model = License
        view_name = 'api:v2:license-detail'
        fields = ('id', 'title', 'type')
