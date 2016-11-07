from core.models import (
    AtmosphereUser, AccountProvider, Group, Identity, Provider, Quota
)
from api.v2.serializers.details.credential import CredentialSerializer
from service.driver import get_esh_driver, get_account_driver

from rest_framework import serializers


def create_user(credentials_list, context):
    username_cred = [c for c in credentials_list if c['key'] == 'key']
    request_ctx = context.get('request')
    if request_ctx and hasattr(request_ctx, 'user'):
        return request_ctx.user
    user = context.get('user')
    if user:
        return user
    if not username_cred:
        raise Exception(
            "Could not determine a username to create the Identity. "
            "Pass user as 'created_by' _or_ pass request or user "
            "into the serializer context.")
    username = username_cred[0]['value']
    (user, group) = Group.create_usergroup(username)
    return user


def validate_identity(new_identity):
    try:
        import ipdb;ipdb.set_trace()
        driver = get_esh_driver(new_identity)
        driver.list_sizes()
    except:
        new_identity.delete()
        raise #Exception("The driver created by this identity was invalid")

def attempt_account_creation(new_identity):
    try:
        provider = new_identity.provider
        credentials = new_identity.get_all_credentials()
        acct_driver = get_account_driver(provider, raise_exception=True)
        # NOTE: This is intentionally specific. When we service -other-
        # provider types, this may change.
        # Additionally, we may ingest this *into* the driver and
        # just pass in identity at a later stage.
        acct_driver.build_account(
            credentials.get('key'),
            credentials.get('secret'),
            credentials.get('ex_project_name'),
            credentials.get('role_name'),
            domain_name=credentials.get('domain_name')
        )
    except:
        new_identity.delete()
        raise


class IdentitySerializer(serializers.ModelSerializer):
    """
    #NOTE: Arguably this could be 'AccountSerializer' (because it does more than create an Identity..)

    This is a 'utility serializer' it should be used for preparing a v2 POST *ONLY*
    This serializer should *never* be returned to the user.
    instead, the core provider should be re-serialized into a 'details serializer'
    """
    provider = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=Provider.objects.all())  # FIXME: user-specific queryset required
    created_by = serializers.SlugRelatedField(
        slug_field="username",
        required=False, allow_null=True,
        queryset=AtmosphereUser.objects.all())
    quota = serializers.SlugRelatedField(
        slug_field="uuid",
        required=False, allow_null=True,
        queryset=Quota.objects.all())  # FIXME: user-specific queryset required
    create_account = serializers.BooleanField(default=False)
    admin_account = serializers.BooleanField(default=False)
    credentials = CredentialSerializer(many=True)

    def create(self, validated_data):
        ident_kwargs = validated_data.copy()
        create_account = ident_kwargs.pop('create_account')
        admin_account = ident_kwargs.pop('admin_account')
        credentials_list = ident_kwargs.pop('credentials')
        context = self.context
        if 'created_by' not in ident_kwargs:
            user = create_user(credentials_list, context)
            ident_kwargs['created_by'] = user
        if 'quota' not in ident_kwargs:
            quota = Quota.default_quota()
            ident_kwargs['quota'] = quota
        new_identity = Identity.objects.create(
            **ident_kwargs)
        # Add credentials to identity
        for cred in credentials_list:
            new_identity.credential_set.get_or_create(
                key=cred['key'],
                value=cred['value'])
        # If admin_account, create an AccountProvider
        if admin_account:
            AccountProvider.objects.get_or_create(
                provider=new_identity.provider,
                identity=new_identity)
        # If create_account, build it. If it fails, destroy before returning.
        if create_account:
            attempt_account_creation(
                new_identity)
        validate_identity(new_identity)
        return new_identity

    class Meta:
        model = Identity
        fields = (
            'id',
            'uuid',
            'admin_account',
            'create_account',
            'created_by',
            'credentials',
            'provider',
            'quota'
        )
