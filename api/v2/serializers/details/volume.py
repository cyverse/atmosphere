from core.models import Volume
from rest_framework import serializers
from api.v2.serializers.summaries import (
    ProviderSummarySerializer,
    UserSummarySerializer,
    IdentitySummarySerializer
)


class VolumeSerializer(serializers.HyperlinkedModelSerializer):
    provider = ProviderSummarySerializer(source='instance_source.provider')
    identity = IdentitySummarySerializer(source='instance_source.created_by_identity')
    user = UserSummarySerializer(source='instance_source.created_by')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')
    projects = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    uuid = serializers.CharField(source='instance_source.identifier')

    class Meta:
        model = Volume
        view_name = 'api_v2:volume-detail'
        fields = ('id', 'uuid', 'url', 'name', 'size', 'user', 'provider', 'identity', 'projects', 'start_date', 'end_date')

    def update(self, instance, validated_data):
        if 'instance_source' in validated_data:
            source = instance.instance_source
            source_data = validated_data.pop('instance_source')
            for key, val in source_data.items():
                setattr(source, key, val)
            source.save()
        for (key, val) in validated_data.items():
            setattr(instance, key, val)
        instance.save()
        return instance
