from core.models import ProviderMachine
from rest_framework import serializers
from .provider import ProviderSummarySerializer


class ProviderMachineSummarySerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.ReadOnlyField(source='instance_source.identifier')
    provider = ProviderSummarySerializer(source='instance_source.provider')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')
    #licenses = LicenseSerializer(many=True) #NEW
    #members = MachineMembershipSerializer(many=True) #NEW

    class Meta:
        model = ProviderMachine
        view_name = 'api:v2:providermachine-detail'
        fields = ('id', 'uuid', 'url', 'provider',
                'start_date', 'end_date')
        #TODO: add 'application_version'
