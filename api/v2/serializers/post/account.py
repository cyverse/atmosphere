from core.models import (
    AtmosphereUser, AccountProvider, Group, Identity, Provider, Quota
)
from core.query import only_current
from api.v2.serializers.details.credential import CredentialSerializer
from service.driver import get_esh_driver, get_account_driver

from rest_framework import serializers


class AccountSerializer(serializers.Serializer):
    """
    """
    # Flags
    create_account = serializers.BooleanField(default=False)
    admin_account = serializers.BooleanField(default=False)
    # Fields
    atmo_user = serializers.CharField()
    atmo_group = serializers.CharField()
    provider = serializers.UUIDField(format='hex_verbose')
    credentials = CredentialSerializer(many=True)
    # Optional fields
    quota = serializers.UUIDField(required=False, allow_null=True)
    allocation_source_id = serializers.CharField(required=False, allow_null=True)

    def _validate_user_group(self, data):
        username = data['atmo_user']
        groupname = data['atmo_group']
        create_account = data['create_account']
        if not create_account:
            atmo_user = AtmosphereUser.objects.filter(username=username).first()
            if not atmo_user:
                raise serializers.ValidationError(
                    "User %s does not exist. Validation failed because "
                    "create_account is set to False" % username)
            atmo_group = Group.objects.filter(user=atmo_user).filter(name=groupname).first()
            if not atmo_group:
                raise serializers.ValidationError(
                    "Group %s does not exist and/or does not belong to user %s. "
                    "Validation failed because create_account is set to False"
                    % (groupname, username))
        else:
            atmo_user, atmo_group = Group.create_usergroup(username, groupname)
        return (atmo_user, atmo_group)

    def _validate_provider(self, data):
        provider_uuid = data.get('provider', '')
        provider = Provider.objects.filter(only_current(), active=True).filter(uuid=provider_uuid).first()
        if not provider:
            raise serializers.ValidationError(
                "Provider %s does not exist" % provider)
        return provider

    def _validate_quota(self, data):
        quota_uuid = data.get('quota', '')
        quota = Quota.objects.filter(uuid=quota_uuid).first()
        if quota_uuid and not quota:
            raise serializers.ValidationError(
                "Quota %s does not exist" % quota)
        elif not quota:
            quota = Quota.default_quota()
        return quota

    def _validate_allocation(self, data):
        # FIXME: Validation of allocation source logic goes *here*
        return None

    def _validate_openstack_credentials(self, data):
        credentials = data['credentials']
        create_account = data['create_account']
        keys = [c['key'] for c in credentials]
        if create_account:
            required_keys = ['key']
        else:
            required_keys = ['key', 'secret', 'ex_project_name']
        missing_keys = [key for key in required_keys if key not in keys]
        if missing_keys:
            raise serializers.ValidationError("Missing required key(s) for Openstack creation: %s" % missing_keys)
        return credentials

    def _validate_credentials(self, provider, data):
        # FIXME: Validation of credentials based on the selected provider
        provider_type = provider.get_type_name().lower()
        credentials = data['credentials']
        if provider_type == 'openstack':
            valid_creds = self._validate_openstack_credentials(data)
        else:
            valid_creds = credentials
        return valid_creds

    def validate(self, data):
        validated_data = data
        # Validate that user/group *does not exist* and *create_account* is True, or that user/group is 'visible'
        atmo_user, atmo_group = self._validate_user_group(data)
        validated_data['atmo_user'] = atmo_user
        validated_data['atmo_group'] = atmo_group

        # Validate that provider is 'visible' for the user
        validated_data['provider'] = self._validate_provider(data)
        # Validate that the quota exists (Or set a default)
        validated_data['quota'] = self._validate_quota(data)
        # Validate that the allocation source exists (Or set a default)
        validated_data['allocation_source'] = self._validate_allocation(data)
        # Validate the credentials (?)
        validated_data['credentials'] = self._validate_credentials(validated_data['provider'], data)
        return validated_data

    def create_openstack_account(self, provider, validated_data):
        acct_driver = get_account_driver(provider, raise_exception=True)
        provider = validated_data['provider']
        quota = validated_data['quota']
        user = validated_data['atmo_user']
        credentials_list = validated_data['credentials']
        credentials = {c['key']:c['value'] for c in credentials_list}
        (username, password, project) = acct_driver.build_account(
            credentials.get('key'),
            credentials.get('secret'),
            credentials.get('ex_project_name'),
            credentials.get('role_name'),
            domain_name=credentials.get('domain_name')
        )
        credentials['key'] = username
        credentials['secret'] = password
        credentials['ex_project_name'] = project.name
        # Create identity using serializer kwargs
        new_identity = Identity.objects.create(
            created_by=user,
            provider=provider,
            quota=quota)
        for key, value in credentials.items():
            new_identity.credential_set.get_or_create(
                key=key, value=value)
        return new_identity

    def create(self, validated_data):
        ident_kwargs = validated_data.copy()
        admin_account = ident_kwargs.pop('admin_account')
        group = ident_kwargs.pop('atmo_group')
        provider = ident_kwargs['provider']
        quota = ident_kwargs['quota']
        provider_type = provider.get_type_name().lower()
        if provider_type == 'openstack':
            new_identity = self.create_openstack_account(provider, validated_data)
        else:
            raise Exception("Cannot create accounts for provider of type %s" % provider_type)
        # Add the credentials to identity post-creation
        new_identity.share(group, quota=quota)
        # If admin_account, create an AccountProvider
        if admin_account:
            AccountProvider.objects.get_or_create(
                provider=new_identity.provider,
                identity=new_identity)
        validate_identity(new_identity)
        return new_identity

    class Meta:
        fields = (
            'allocation_source_id',
            'atmo_user',
            'atmo_group',
            'admin_account',
            'create_account',
            'credentials',
            'provider',
            'quota'
        )


def validate_identity(new_identity):
    try:
        driver = get_esh_driver(new_identity)
        driver.list_sizes()
    except:
        new_identity.delete()
        raise #Exception("The driver created by this identity was invalid")
