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
    class Meta:
        model = ProviderMachine
        fields = ('id', 'uuid', 'url', 'provider', 'version', 'owner',
                  'start_date', 'end_date')
