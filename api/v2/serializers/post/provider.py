from core.models import (
    InstanceAction, Provider, PlatformType, ProviderType)
from rest_framework import serializers
from api.v2.serializers.details.provider_credential import ProviderCredentialSerializer


class ProviderSerializer(serializers.ModelSerializer):
    """
    This is a 'utility serializer' it should be used for preparing a v2 POST *ONLY*

    This serializer should *never* be returned to the user.
    instead, the core provider should be re-serialized into a 'details serializer'
    """
    name = serializers.CharField(source='location')
    type = serializers.SlugRelatedField(
        slug_field="name",
        default='KVM',
        queryset=ProviderType.objects.all())
    platform = serializers.SlugRelatedField(
        source='virtualization',
        slug_field="name",
        queryset=PlatformType.objects.all())
    over_allocation_action = serializers.SlugRelatedField(
        slug_field="name",
        queryset=InstanceAction.objects.all(),
        default=None, required=False, allow_null=True)
    public = serializers.BooleanField(default=True)
    active = serializers.BooleanField(default=True)
    auto_imaging = serializers.BooleanField(default=True)
    description = serializers.CharField(default="")
    cloud_config = serializers.DictField()
    credentials = ProviderCredentialSerializer(many=True)

    def create(self, validated_data):
        prov_kwargs = validated_data.copy()
        credentials_list = prov_kwargs.pop('credentials')
        new_provider = Provider.objects.create(**prov_kwargs)
        for cred in credentials_list:
            new_provider.providercredential_set.get_or_create(
                key=cred['key'],
                value=cred['value'])
        return new_provider

    class Meta:
        model = Provider
        fields = (
            'id',
            'uuid',
            'name',
            'type',
            'platform',
            'over_allocation_action',
            'public',
            'active',
            'auto_imaging',
            'timezone',
            'description',
            'cloud_config',
            'credentials'
        )
