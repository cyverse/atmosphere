from core.models import ProviderMachine
from rest_framework import serializers
from .provider import ProviderSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ProviderMachineSummarySerializer(serializers.HyperlinkedModelSerializer):
    provider = ProviderSummarySerializer(source='instance_source.provider')
    version = serializers.ReadOnlyField(source='application_version.name')
    owner = serializers.ReadOnlyField(
        source='application_version.application.created_by.username')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')
    uuid = serializers.ReadOnlyField(source='instance_source.identifier')
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:providermachine-detail',
        uuid_field='identifier',
    )
    launch_success = serializers.SerializerMethodField()
    launch_failure = serializers.SerializerMethodField()

    def get_launch_failure(self, prov_machine):
        inactive_instance_num = prov_machine.failed_instances().count()
        return inactive_instance_num

    def get_launch_success(self, prov_machine):
        active_instance_num = prov_machine.active_instances().count()
        return active_instance_num

    class Meta:
        model = ProviderMachine
        fields = ('id', 'uuid', 'url', 'provider', 'version', 'owner',
                  'start_date', 'end_date', 'launch_success', 'launch_failure')
