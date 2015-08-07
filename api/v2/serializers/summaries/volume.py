from core.models import Volume
from rest_framework import serializers
from .identity import IdentitySummarySerializer


class VolumeSummarySerializer(serializers.HyperlinkedModelSerializer):
    identity = IdentitySummarySerializer(
        source='instance_source.created_by_identity')
    provider = serializers.PrimaryKeyRelatedField(
        source='instance_source.provider',
        read_only=True)
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')
    uuid = serializers.CharField(source='instance_source.identifier')

    class Meta:
        model = Volume
        view_name = 'api:v2:volume-detail'
        fields = (
            'id',
            'uuid',
            'url',
            'name',
            'size',
            'identity',
            'provider',
            'start_date',
            'end_date')
