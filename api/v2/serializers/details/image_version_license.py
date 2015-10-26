from rest_framework import serializers

from core.models import ApplicationVersionLicense as ImageVersionLicense
from core.models import ApplicationVersion as ImageVersion
from core.models import License

from api.v2.serializers.summaries import (
    ImageVersionSummarySerializer, LicenseSummarySerializer)


class ImageVersionRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return ImageVersion.objects.all()

    def to_representation(self, value):
        image_version = ImageVersion.objects.get(pk=value.pk)
        serializer = ImageVersionSummarySerializer(
            image_version,
            context=self.context)
        return serializer.data


class LicenseRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return License.objects.all()

    def to_representation(self, value):
        license = License.objects.get(pk=value.pk)
        serializer = LicenseSummarySerializer(license, context=self.context)
        return serializer.data


class ImageVersionLicenseSerializer(serializers.HyperlinkedModelSerializer):
    image_version = ImageVersionRelatedField(
        queryset=ImageVersion.objects.none(), source='applicationversion')
    license = LicenseRelatedField(
        queryset=License.objects.none())
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:imageversion_license-detail',
    )
    class Meta:
        model = ImageVersionLicense
        fields = (
            'id',
            'url',
            'image_version',
            'license'
        )
