from core.models import License
from rest_framework import serializers


class LicenseSerializer(serializers.HyperlinkedModelSerializer):
    #TODO: type --> type_name
    class Meta:
        model = License
        view_name = 'api_v2:license-detail'
        fields = ('id', 'title', 'license_type', 'license_text')
