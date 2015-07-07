from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers
from api.v2.serializers.summaries import LicenseSerializer
from api.v2.serializers.fields import ProviderMachineRelatedField


class ImageVersionSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for ApplicationVersion (aka 'image_version')
    """
    #NOTE: Implicitly included via 'fields'
    # id, application
    parent = serializers.HyperlinkedRelatedField(
        view_name="applicationversion-detail",
        read_only=True)
    #name, change_log, allow_imaging
    licenses = LicenseSerializer(many=True, read_only=True) #NEW
    membership = serializers.SlugRelatedField(slug_field='name', read_only=True, many=True) #NEW
    machines = ProviderMachineRelatedField(many=True)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    class Meta:
        model = ImageVersion
        view_name = 'api:v2:providermachine-detail'
        fields = ('id', 'parent', 'name', 'change_log',
                'machines', 'allow_imaging',
                'licenses','membership',
                'start_date', 'end_date')
