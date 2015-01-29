from core.models.license import License
from rest_framework import serializers


class POST_LicenseSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='username')
    type = serializers.SlugRelatedField(source='license_type', slug_field='name')
    class Meta:
        model = License
        exclude = ("license_type",)