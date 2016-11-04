from core.models import (
    Identity, Provider, Quota
)
from rest_framework import serializers


class IdentitySerializer(serializers.ModelSerializer):
    """
    This is a 'utility serializer' it should be used for preparing a v2 POST *ONLY*

    This serializer should *never* be returned to the user.
    instead, the core provider should be re-serialized into a 'details serializer'
    """
    provider = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=Provider.objects.all())  #FIXME: user-specific queryset required
    quota = serializers.SlugRelatedField(
        slug_field="uuid",
        required=False, allow_null=True,
        queryset=Quota.objects.all())  #FIXME: user-specific queryset required
    create_account = serializers.BooleanField(default=False)
    admin_account = serializers.BooleanField(default=False)
    credentials = serializers.DictField()

    def create(self, validated_data):
        ident_kwargs = validated_data.copy()
        create_account = ident_kwargs.pop('create_account')
        admin_account = ident_kwargs.pop('admin_account')
        credentials = ident_kwargs.pop('credentials')
        new_identity = Identity.objects.create(**ident_kwargs)
        for c_key, c_value in credentials.items():
            new_identity.credential_set.get_or_create(
                key=c_key,
                value=c_value)
        import ipdb;ipdb.set_trace()
        # If create_account, build it.
        # If admin_account, create an AccountProvider
        return new_identity

    class Meta:
        model = Identity
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


