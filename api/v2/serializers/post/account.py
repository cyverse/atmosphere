from core.models import (
    AtmosphereUser, AccountProvider, Group, Identity, Provider, Quota
)
from core.query import only_current, contains_credential
from api.v2.serializers.details.credential import CredentialSerializer
from service.driver import get_esh_driver, get_account_driver
from rtwo.exceptions import KeystoneUnauthorized

from rest_framework import serializers


class AccountSerializer(serializers.Serializer):
    """
    """
    # Flags
    create_account = serializers.BooleanField(default=False, write_only=True)
    admin_account = serializers.BooleanField(default=False, write_only=True)
    # Fields
    atmo_user = serializers.CharField(write_only=True)
    atmo_group = serializers.CharField(write_only=True)
    provider = serializers.UUIDField(format='hex_verbose')
    credentials = CredentialSerializer(many=True, write_only=True)
    # Optional fields
    quota = serializers.UUIDField(required=False, allow_null=True)
    #Remove? allocation_source_id = serializers.CharField(required=False, allow_null=True)

    def _validate_user_group(self, data):
        username = data['atmo_user']
        groupname = data['atmo_group']
        atmo_user = AtmosphereUser.objects.filter(username=username).first()
        if atmo_user:
            atmo_group = Group.objects.filter(user=atmo_user).filter(name=groupname).first()
        else:
            atmo_group = None
        if not atmo_user or not atmo_group:
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
        if not quota_uuid:
            return Quota.default_quota()

        quota = Quota.objects.filter(uuid=quota_uuid).first()
        if not quota:
            raise serializers.ValidationError(
                "Quota %s does not exist" % quota)
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

    def _get_request_user(self):
        if 'request' in self.context:
            return self.context['request'].user
        elif 'user' in self.context:
            return self.context['user']
        else:
            raise ValueError("Expected 'request/user' to be passed in via context for this serializer")

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

        # Using the validated data, ensure the user *should* be able to request these things.
        self.validate_user(validated_data)
        if not validated_data['admin_account']:
            self.validate_account_driver(validated_data)
        return validated_data

    def validate_account_driver(self, validated_data):
        try:
            provider = validated_data['provider']
            acct_driver = get_account_driver(provider, raise_exception=True)
            return acct_driver
        except Exception as exc:
            raise serializers.ValidationError("Attempting to create an account for provider %s failed. Message: %s" % (provider, exc.message))

    def validate_user(self, validated_data):
        request_user = self._get_request_user()
        # Tests or restrictions on request-user go here
        if request_user.is_staff or request_user.is_superuser:
            return
        if request_user.admin_providers.filter(id=validated_data['provider'].id).count() > 0:
            return
        raise serializers.ValidationError("Only the Cloud Administrators can create new accounts")

    def _create_openstack_account(self, provider, credentials):
        """
        Given a Core.provider and a 'credentials dict'
        Create an openstack account.
        """
        acct_driver = get_account_driver(provider, raise_exception=True)
        try:
            (username, password, project) = acct_driver.build_account(
                credentials.get('key'),
                credentials.get('secret'),
                credentials.get('ex_project_name'),
                credentials.get('role_name'),
                domain_name=credentials.get('domain_name')
            )
        except KeystoneUnauthorized:
            raise serializers.ValidationError("The credentials used to create this account are invalid. Double-check your credentials and try again.")
        except:
            raise serializers.ValidationError("Error creating the account - %s")
        return username, password, project

    def create_openstack_identity(self, provider, validated_data):
        admin_account = validated_data['admin_account']
        create_account = validated_data['create_account']
        provider = validated_data['provider']
        quota = validated_data['quota']
        user = validated_data['atmo_user']
        credentials_list = validated_data['credentials']
        credentials = {c['key']: c['value'] for c in credentials_list}

        if create_account:
            (username, password, project) = self._create_openstack_account(provider, credentials)
            credentials['key'] = username
            credentials['secret'] = password
            credentials['ex_project_name'] = project.name
        try:
            identity = Identity.objects.get(
                contains_credential('key', 'username'),
                created_by=user,
                provider=provider,
                quota=quota)
        except Identity.DoesNotExist:
            identity = Identity.objects.create(
                created_by=user,
                provider=provider,
                quota=quota)
        # Identity-container at-most-one per account (per user creating it)
        for key, value in credentials.items():
            identity.credential_set.get_or_create(
                key=key, value=value)
        return identity

    def create(self, validated_data):
        ident_kwargs = validated_data.copy()
        admin_account = ident_kwargs.pop('admin_account')
        group = ident_kwargs.pop('atmo_group')
        provider = ident_kwargs['provider']
        quota = ident_kwargs['quota']
        provider_type = provider.get_type_name().lower()
        if provider_type == 'openstack':
            new_identity = self.create_openstack_identity(provider, validated_data)
        else:
            raise Exception("Cannot create accounts for provider of type %s" % provider_type)
        # Add the credentials to identity post-creation
        new_identity.share(group, quota=quota)
        # If admin_account, create an AccountProvider
        if admin_account:
            AccountProvider.objects.get_or_create(
                provider=new_identity.provider,
                identity=new_identity)
        #TODO: When the refactor of rtwo/get_esh_driver is complete, validate_identity should be call-able without the django model (to avoid create-then-delete)
        validate_identity(new_identity)
        return new_identity

    class Meta:
        fields = (
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
        raise # Exception("The driver created by this identity was invalid")
