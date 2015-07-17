from core.models.license import License, LicenseType
from core.models.user import AtmosphereUser
from rest_framework import serializers


class POST_LicenseSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(
        slug_field='username',
        queryset=AtmosphereUser.objects.all())
    type = serializers.SlugRelatedField(
        source='license_type',
        slug_field='name',
        queryset=LicenseType.objects.all())

    class Meta:
        model = License
        exclude = ("license_type",)
