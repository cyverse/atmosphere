from rest_framework import serializers
from core.models import License
from .license_serializer import LicenseSerializer


class LicenseRelatedField(serializers.PrimaryKeyRelatedField):

    def get_queryset(self):
        return License.objects.all()

    def to_representation(self, value):
        license = License.objects.get(pk=value.pk)
        serializer = LicenseSerializer(license, context=self.context)
        return serializer.data

