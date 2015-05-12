from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer, LicenseSerializer, ImageSummarySerializer


class ImageVersionSerializer(serializers.HyperlinkedModelSerializer):

    # id, application
    fork_version = serializers.HyperlinkedRelatedField(
        view_name="applicationversion-detail",
        read_only=True)
    #name, description, icon, allow_imaging
    licenses = LicenseSerializer(many=True, read_only=True) #NEW
    membership = serializers.SlugRelatedField(slug_field='name', read_only=True, many=True) #NEW
    image = ImageSummarySerializer(source='application')
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    class Meta:
        model = ImageVersion
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'fork_version', 'name', 'description',
                'icon', 'image', 'allow_imaging', 'licenses','membership',
                'start_date', 'end_date')
