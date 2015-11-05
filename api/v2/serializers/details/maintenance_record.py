from core.models import MaintenanceRecord, Provider
from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.summaries import ProviderSummarySerializer
from rest_framework import serializers


class MaintenanceRecordSerializer(serializers.HyperlinkedModelSerializer):
    provider = ModelRelatedField(
        lookup_field='name',
        queryset=Provider.objects.all(),
        serializer_class=ProviderSummarySerializer,
        style={'base_template': 'input.html'})
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:maintenancerecord-detail',
    )

    def create(self, validated_data):
        raise NotImplemented("Creating Maintenance Records from API is not allowed.")

    class Meta:
        model = MaintenanceRecord
        fields = ('id', 'url', 'start_date', 'end_date', 'title', 'message', 'provider', 'disable_login')
