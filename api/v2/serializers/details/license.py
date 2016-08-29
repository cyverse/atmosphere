from core.models import License, LicenseType, AtmosphereUser
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.summaries import LicenseTypeSummarySerializer
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class LicenseSerializer(serializers.HyperlinkedModelSerializer):
    text = serializers.CharField(source='license_text')
    type = ModelRelatedField(
        lookup_field='name',
        source='license_type',
        queryset=LicenseType.objects.all(),
        serializer_class=LicenseTypeSummarySerializer,
        style={'base_template': 'input.html'})
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:license-detail',
    )
    created_by = serializers.SlugRelatedField(
        slug_field='username', queryset=AtmosphereUser.objects.all(),
        required=False)

    def is_valid(self, raise_exception=False):
        """
        """
        raw_type = self.initial_data.get("type", "").lower()
        if 'raw text' in raw_type:
            LicenseType.objects.get_or_create(name="Raw Text")
        elif 'url' in raw_type:
            LicenseType.objects.get_or_create(name="URL")
        return super(LicenseSerializer, self).is_valid(
                raise_exception=raise_exception)

    def create(self, validated_data):

        if 'created_by' not in validated_data:
            request = self.context.get('request')
            if request and request.user:
                validated_data['created_by'] = request.user
        return super(LicenseSerializer, self).create(validated_data)

    class Meta:
        model = License
        fields = ('id', 'url', 'uuid', 'created_by', 'title', 'text', 'type')
