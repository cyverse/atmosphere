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
        default='OpenStack',
        queryset=ProviderType.objects.all())
    platform = serializers.SlugRelatedField(
        source='virtualization',
        default='KVM', required=False, allow_null=True,
        slug_field="name",
        queryset=PlatformType.objects.all())
    over_allocation_action = serializers.SlugRelatedField(
        slug_field="name",
        queryset=InstanceAction.objects.all(),
        default=None, required=False, allow_null=True)
    public = serializers.BooleanField(default=False)
    active = serializers.BooleanField(default=True)
    auto_imaging = serializers.BooleanField(default=True)
    description = serializers.CharField(default="")
    cloud_config = serializers.DictField()
    credentials = ProviderCredentialSerializer(many=True)

    def _get_request_user(self, raise_exception=True):
        if 'request' in self.context:
            return self.context['request'].user
        elif 'user' in self.context:
            return self.context['user']
        elif raise_exception:
            raise ValueError("Expected 'request/user' to be passed in via context for this serializer")
        return None

    def validate(self, data):
        validated_data = data

        request_user = self._get_request_user(raise_exception=False)
        validated_data['cloud_admin'] = request_user
        if not request_user.is_admin():
            raise serializers.ValidationError("Only an admin user can create a new Provider")

        if type(data['type']) == str:
            validated_data['type'] = ProviderType.objects.get(name=data['type'])
        if not validated_data['type']:
            raise serializers.ValidationError("Invalid Provider type %s" % data['type'])

        if type(data['virtualization']) == str:
            validated_data['virtualization'] = PlatformType.objects.filter(name=data['virtualization']).first()
        if not validated_data['virtualization']:
            raise serializers.ValidationError("Invalid platform type %s" % data['virtualization'])
        return validated_data

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
