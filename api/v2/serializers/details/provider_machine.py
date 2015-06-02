from core.models import ProviderMachine
from rest_framework import serializers
from api.v2.serializers.summaries import ImageSummarySerializer, ProviderSummarySerializer, UserSummarySerializer


class ProviderMachineSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.ReadOnlyField(source='instance_source.identifier')
    image = ImageSummarySerializer(source='application')
    provider = ProviderSummarySerializer(source='instance_source.provider')
    created_by = UserSummarySerializer(source='instance_source.created_by')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')

    class Meta:
        model = ProviderMachine
        view_name = 'api:v2:providermachine-detail'
        fields = ('id', 'uuid', 'url', 'image', 'provider', 'created_by', 'start_date', 'end_date')
