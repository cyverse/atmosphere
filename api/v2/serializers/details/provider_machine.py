from core.models import ProviderMachine
from rest_framework import serializers
from api.v2.serializers.summaries import (
        ImageSummarySerializer, ImageVersionSummarySerializer,
        ProviderSummarySerializer, UserSummarySerializer,
        LicenseSummarySerializer)
from api.v2.serializers.fields.base import InstanceSourceHyperlinkedIdentityField


class ProviderMachineSerializer(serializers.HyperlinkedModelSerializer):
    # NOTE: these fields could be generalized for reuse in VolumeSerializer
    uuid = serializers.ReadOnlyField(source='instance_source.identifier')
    provider = ProviderSummarySerializer(source='instance_source.provider')
    version = ImageVersionSummarySerializer(source='application_version')
    image = ImageSummarySerializer(source='application')
    created_by = UserSummarySerializer(source='instance_source.created_by')
    start_date = serializers.DateTimeField(source='instance_source.start_date')
    end_date = serializers.DateTimeField(source='instance_source.end_date',
                                         allow_null=True)
    licenses = LicenseSummarySerializer(many=True, read_only=True)  # NEW
    members = serializers.SlugRelatedField(
        slug_field='name',
        read_only=True,
        many=True)  # NEW
    # NOTE: this is still using ID instead of UUID -- due to abstract classes and use of getattr in L271 of rest_framework/relations.py, this is a 'kink' that has not been worked out yet.
    url = InstanceSourceHyperlinkedIdentityField(
        view_name='api:v2:providermachine-detail',
    )

    class Meta:
        model = ProviderMachine
        fields = ('id', 'uuid', 'url', 'provider', 'image',
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
