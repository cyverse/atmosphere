from core.models import License, LicenseType
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class LicenseSummarySerializer(serializers.HyperlinkedModelSerializer):
    type = serializers.SlugRelatedField(
        source='license_type',
        slug_field='name',
        queryset=LicenseType.objects.all())
    text = serializers.CharField(source='license_text', read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:license-detail',
    )
    class Meta:
        model = License
        fields = ('id', 'url', 'uuid', 'title', 'type', 'text')
