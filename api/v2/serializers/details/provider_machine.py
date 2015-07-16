from core.models import ProviderMachine
from rest_framework import serializers
from api.v2.serializers.summaries import ImageVersionSummarySerializer, ProviderSummarySerializer, UserSummarySerializer, LicenseSerializer


class ProviderMachineSerializer(serializers.HyperlinkedModelSerializer):
    #NOTE: these fields could be generalized for reuse in VolumeSerializer
    uuid = serializers.ReadOnlyField(source='instance_source.identifier')
    provider = ProviderSummarySerializer(source='instance_source.provider')
    version = ImageVersionSummarySerializer(source='application_version')
    created_by = UserSummarySerializer(source='instance_source.created_by')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')
    licenses = LicenseSerializer(many=True, read_only=True) #NEW
    members = serializers.SlugRelatedField(slug_field='name', read_only=True, many=True) #NEW
    

    class Meta:
        model = ProviderMachine
        view_name = 'api:v2:providermachine-detail'
        fields = ('id', 'uuid', 'url', 'provider',
                'licenses', 'members', 'version',
                'created_by', 'start_date', 'end_date')


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
