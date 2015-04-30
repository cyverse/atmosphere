from core.models import ProviderMachine
from rest_framework import serializers
from api.v2.serializers.summaries import ImageSummarySerializer, ProviderSummarySerializer, UserSummarySerializer, LicenseSerializer


class ProviderMachineSerializer(serializers.HyperlinkedModelSerializer):
    uuid = serializers.ReadOnlyField(source='instance_source.identifier')
    image = ImageSummarySerializer(source='application')
    provider = ProviderSummarySerializer(source='instance_source.provider')
    created_by = UserSummarySerializer(source='instance_source.created_by')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date')
    licenses = LicenseSerializer(many=True, read_only=True) #NEW
    #members = MachineMembershipSerializer(many=True) #NEW

    class Meta:
        model = ProviderMachine
        view_name = 'api_v2:providermachine-detail'
        fields = ('id', 'uuid', 'url', 'image', 'provider',
                'licenses', 'allow_imaging', 'version',
                'created_by', 'start_date', 'end_date')

    #def create(self, validated_data):
    #    return ProviderMachine(**validated_data)

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
