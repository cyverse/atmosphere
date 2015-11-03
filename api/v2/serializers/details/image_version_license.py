from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.models import ApplicationVersionLicense as ImageVersionLicense
from core.models import ApplicationVersion as ImageVersion
from core.models import License

from api.v2.serializers.summaries import (
    ImageVersionSummarySerializer, LicenseSummarySerializer)
from api.v2.serializers.fields.base import ModelRelatedField


class ImageVersionLicenseSerializer(serializers.HyperlinkedModelSerializer):
    image_version = ModelRelatedField(
        queryset=ImageVersion.objects.all(),
        serializer_class=ImageVersionSummarySerializer,
        style={'base_template': 'input.html'},
        required=False)
    license = ModelRelatedField(
        queryset=License.objects.all(),
        serializer_class=LicenseSummarySerializer,
        style={'base_template': 'input.html'},
        lookup_field='uuid',
        required=False)
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:imageversion_license-detail',
    )
    class Meta:
        model = ImageVersionLicense
        validators = [
            UniqueTogetherValidator(
                queryset=ImageVersionLicense.objects.all(),
                fields=('image_version', 'license')
            )
        ]
        fields = (
            'id',
            'url',
            'image_version',
            'license'
        )
