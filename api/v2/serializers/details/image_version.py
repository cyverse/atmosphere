from core.models import ApplicationVersion as ImageVersion
from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer, LicenseSerializer


class ImageVersionSerializer(serializers.HyperlinkedModelSerializer):
    def get_membership_queryset(self, *args, **kwargs):
        import ipdb;ipdb.set_trace()
        return ApplicationVersion.objects.all()

    # id, application
    fork_version = serializers.HyperlinkedRelatedField(
        view_name="applicationversion-detail",
        read_only=True)
    #name, description, icon, allow_imaging
    licenses = LicenseSerializer(many=True, read_only=True) #NEW
    membership = serializers.SlugRelatedField(slug_field='name', queryset=get_membership_queryset, many=True) #NEW
    created_by = UserSummarySerializer(source='application.created_by')
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    class Meta:
        model = ImageVersion
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'fork_version', 'name', 'description',
                'icon', 'allow_imaging', 'licenses','membership',
                'start_date', 'end_date', 'created_by')
