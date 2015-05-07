from core.models import ApplicationVersion
from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer, LicenseSerializer


class ApplicationVersionSerializer(serializers.HyperlinkedModelSerializer):
    # id, application
    fork_version = serializers.HyperlinkedRelatedField(
        view_name="applicationversion-detail",
        read_only=True)
    #name, description, icon, allow_imaging
    licenses = LicenseSerializer(many=True, read_only=True) #NEW
    #membership = VersionMembershipSerializer(many=True) #NEW
    created_by = UserSummarySerializer(source='application.created_by')
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    class Meta:
        model = ApplicationVersion
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'fork_version', 'name', 'description',
                'icon', 'allow_imaging', 'licenses',
                'start_date', 'end_date', 'created_by')
