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
    #allocation_source_id = serializers.CharField(required=False, allow_null=True)  NOTE: Uncomment when feature is completed

    def validate(self, data):
        """
        Validation will:
        - Ensure that user/group exists (Or create it)
        - 
        """
        validated_data = data
        self.validate_user(data['provider'])

        validated_data['atmo_user'], validated_data['atmo_group'] = self._validate_user_group(data)
        validated_data['provider'] = self._validate_provider(data['provider'])

        # Using the validated data, ensure the user *should* be able to request these things.

        # Validate that the quota exists (Or set a default)
        validated_data['quota'] = self._validate_quota(data)

        # Validate that the allocation source exists (Or set a default)
        # validated_data['allocation_source'] = self._validate_allocation(data)  NOTE: Uncomment when feature is completed

        # Validate the credentials (?)

        # NOTE: This method is OpenStack specific. Update this method when adding new provider types.
        required_keys = self._get_required_keys(
            validated_data['provider'], validated_data['create_account'])
        validated_data['credentials'] = self._validate_credentials(
            validated_data['provider'], data['credentials'], required_keys)

        if not validated_data['admin_account']:
            self.validate_account_driver(validated_data)
        return validated_data

    def create(self, validated_data):
        username = validated_data['atmo_user']
        groupname = validated_data['atmo_group']
        atmo_user, atmo_group = Group.create_usergroup(
            username, groupname)

        provider = validated_data['provider']
        provider_type = provider.get_type_name().lower()
        if provider_type == 'openstack':
            new_identity = self.create_openstack_identity(atmo_user, provider, validated_data)
        else:
            raise Exception("Cannot create accounts for provider of type %s" % provider_type)

        # Always share identity with group (To enable Troposphere access)
        new_identity.share(atmo_group)

        admin_account = validated_data['admin_account']
        if admin_account:
            AccountProvider.objects.get_or_create(
                provider=new_identity.provider,
                identity=new_identity)

        # TODO: When the refactor of rtwo/get_esh_driver is complete, validate_identity should be call-able without the django model (to avoid create-then-delete)
        validate_identity(new_identity)
        return new_identity

    ###
    # Private validation methods
    ###

    def _validate_user_group(self, data):
        create_account = data['create_account']
        username = data['atmo_user']
        groupname = data['atmo_group']
        atmo_user = AtmosphereUser.objects.filter(username=username).first()
        if atmo_user:
            atmo_group = Group.objects.filter(user=atmo_user).filter(name=groupname).first()
        else:
            atmo_group = None
        if not atmo_user and not create_account:
            raise serializers.ValidationError("User %s does not exist, and 'create_account' is False." % username)
        if not atmo_group and not create_account:
            raise serializers.ValidationError("Group %s does not exist, and 'create_account' is False." % groupname)
        return username, groupname

    def _validate_provider(self, provider_uuid):
        """
        Validate that this provider is 'visible' w.r.t. the current user
        """
        request_user = self._get_request_user()
        # NOTE: With this validation, *ONLY* the creator of the provider can admininster accounts
        # To allow anyone with staff/superuser to create, replace provider_manager
        # provider_manager = Provider.objects
        provider_manager = request_user.admin_providers
        prov_qs = provider_manager.filter(
            only_current(), active=True)
        provider = prov_qs.filter(uuid=provider_uuid).first()
        if not provider:
            raise serializers.ValidationError(
                "Cannot create an account for provider with UUID %s" % provider_uuid)
        return provider

    def _validate_quota(self, data):
        quota_uuid = data.get('quota', '')
        if not quota_uuid:
            return Quota.default_quota()

        quota = Quota.objects.filter(uuid=quota_uuid).first()
        if not quota:
            raise serializers.ValidationError(
                "Quota '%s' not found" % quota_uuid)
        return quota

    def _validate_allocation(self, data):
        # FIXME: Creation & Validation of allocation source logic goes *here* (post-CyVerse+AS)
        return None

    def _validate_openstack_credentials(self, credentials, required_keys):
        """
        Note: If this can be reused elsewhere, we can move this to a class/staticmethod for service.accounts.openstack.AccountDriver
        """
        keys = [c['key'] for c in credentials]
        missing_keys = [key for key in required_keys if key not in keys]
        if missing_keys:
            raise serializers.ValidationError("Missing required key(s) for Openstack creation: %s" % missing_keys)
        return credentials

    def _get_required_keys(self, provider, create_account):
        has_account_provider = provider.accountprovider_set.exists()
        # If an account provider exists, only 'key' is required to create an account
        if create_account and has_account_provider:
            required_keys = ['key']
        else:  # Otherwise require the 'full-chain' credentials
            required_keys = ['key', 'secret', 'ex_project_name']
        return required_keys

    def _validate_credentials(self, provider, credentials, required_keys):
        provider_type = provider.get_type_name().lower()

        # NOTE: Looking to add a new provider type? validate the credentials here!
        if provider_type == 'openstack':
            valid_creds = self._validate_openstack_credentials(credentials, required_keys)
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

    def validate_account_driver(self, validated_data):
        try:
            provider = validated_data['provider']
            acct_driver = get_account_driver(provider, raise_exception=True)
            return acct_driver
        except Exception as exc:
            raise serializers.ValidationError("Attempting to create an account for provider %s failed. Message: %s" % (provider, exc.message))

    def validate_user(self, provider_uuid):
        request_user = self._get_request_user()
        # Tests or restrictions on request-user go here
        if request_user.is_staff or request_user.is_superuser:
            return
        if request_user.admin_providers.filter(uuid=provider_uuid).count() > 0:
            return
        raise serializers.ValidationError("Only the Cloud Administrators can create new accounts")

    ###
    # Private creation methods
    ###

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

    def create_openstack_identity(self, user, provider, validated_data):
        create_account = validated_data['create_account']
        provider = validated_data['provider']
        credentials_list = validated_data['credentials']
        credentials_dict = {c['key']: c['value'] for c in credentials_list}
        has_account_provider = provider.accountprovider_set.exists()
        # Do not create accounts without a valid AccountProvider for the Provider
        if create_account and has_account_provider:
            (username, password, project) = self._create_openstack_account(provider, credentials_dict)
            credentials_dict['key'] = username
            credentials_dict['secret'] = password
            credentials_dict['ex_project_name'] = project.name
        identity = self._get_or_create_identity(user, provider, validated_data['quota'])
        for key, value in credentials_dict.items():
            identity.credential_set.get_or_create(
                key=key, value=value)

        # allocation_source = validated_data['allocation_source']  NOTE: Uncomment when feature is completed
        return identity

    def _get_or_create_identity(self, user, provider, quota):
        try:
            identity = Identity.objects.get(
                contains_credential('key', 'username'),
                created_by=user,
                provider=provider)
            if identity.quota != quota:
                identity.quota = quota
                identity.save()
        except Identity.DoesNotExist:
            identity = Identity.objects.create(
                created_by=user,
                provider=provider,
                quota=quota)
        return identity

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
