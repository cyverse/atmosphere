from core.models.license import License, LicenseType
from rest_framework import serializers


class LicenseSerializer(serializers.ModelSerializer):

    created_by = serializers.SlugRelatedField(slug_field='username', read_only=True)
    type = serializers.SlugRelatedField(source='license_type', slug_field='name',
                                        queryset=LicenseType.objects.all())

    #TODO: Rename THIS field if it makes more sense for API consumers
    allow_imaging = serializers.BooleanField(source='allow_imaging',
                                             read_only=True)

    class Meta:
        model = License
        exclude = ("license_type",)