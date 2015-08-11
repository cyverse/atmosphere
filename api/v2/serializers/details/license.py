from core.models import License, LicenseType
from rest_framework import serializers


class LicenseSerializer(serializers.HyperlinkedModelSerializer):
    text = serializers.CharField(source='license_text')
    type = serializers.SlugRelatedField(
        source='license_type',
        slug_field='name',
        queryset=LicenseType.objects.all())

    def create(self, validated_data):

        if 'created_by' not in validated_data:
            request = self.context.get('request')
            if request and request.user:
                validated_data['created_by'] = request.user
        return super(LicenseSerializer, self).create(validated_data)

    class Meta:
        model = License
        view_name = 'api:v2:license-detail'
        fields = ('id', 'title', 'text', 'type')
