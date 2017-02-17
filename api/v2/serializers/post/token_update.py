from core.models import (
    AtmosphereUser, Identity, Provider
)
from core.query import contains_credential
from service.driver import get_esh_driver
from api.v2.serializers.summaries import IdentitySummarySerializer

from rest_framework import serializers


class TokenUpdateSerializer(serializers.ModelSerializer):
    """
    """
    # Flags
    username = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    project_name = serializers.CharField(write_only=True)
    provider = serializers.UUIDField(format='hex_verbose', write_only=True)
    identity_uuid = serializers.CharField(source='uuid', read_only=True)

    def validate(self, data):
        """
        IF identity is found validation will:
        - Ensure that user/token produces a valid driver
        """
        validated_data = data
        self.validate_token_with_driver(data['provider'], data['username'], data['project_name'], data['token'])
        return validated_data

    def create(self, validated_data):
        identity = self._find_identity_match(validated_data['provider'], validated_data['username'], validated_data['project_name'])
        if not identity:
            identity = self._create_identity(validated_data['provider'], validated_data['username'], validated_data['project_name'], validated_data['token'])
            return identity

        token_cred = identity.credential_set.filter(key='ex_force_auth_token').first()
        if token_cred:
            token_cred.value = validated_data['token']
            token_cred.save()
        else:
            identity.credential_set.create(key='ex_force_auth_token', value=validated_data['token'])
        return identity

    def validate_token_with_driver(self, provider_uuid, username, project_name, new_token_key):
        ident = self._find_identity_match(provider_uuid, username, project_name)
        if not ident:
            # Can't validate driver if identity can't be created.
            return

        try:
            driver = get_esh_driver(ident, identity_kwargs={'ex_force_auth_token': new_token_key})
            if not driver.is_valid():
                raise serializers.ValidationError(
                    "Token returned from keystone could not create an rtwo driver")
        except Exception as exc:
                raise serializers.ValidationError(
                        "Driver could not be created: %s" % exc)

    def _create_identity(self, provider_uuid, username, project_name, token):
        try:
            provider = Provider.objects.get(uuid=provider_uuid)
        except Provider.DoesNotExist:
            raise serializers.ValidationError("Provider %s is invalid" % provider)
        identity = Identity.create_identity(
            username, provider.location,
            cred_key=username, cred_ex_project_name=project_name, cred_ex_force_auth_token=token)
        # FIXME: In a different PR re-work quota to sync with the values in OpenStack. otherwise the value assigned (default) will differ from the users _actual_ quota in openstack.
        self.validate_token_with_driver(provider_uuid, username, project_name, token)
        return identity

    def _find_identity_match(self, provider_uuid, username, project_name):
        try:
            provider = Provider.objects.get(uuid=provider_uuid)
        except Provider.DoesNotExist:
            raise serializers.ValidationError("Provider %s is invalid" % provider)

        request_user = self._get_request_user()
        ident = Identity.objects\
            .filter(
                contains_credential('key', username),
                created_by=request_user, provider=provider)\
            .filter(
                contains_credential('ex_project_name', project_name) | contains_credential('ex_tenant_name', project_name))\
            .first()
        return ident

    def _get_request_user(self):
        if 'request' in self.context:
            return self.context['request'].user
        elif 'user' in self.context:
            return self.context['user']
        else:
            raise ValueError("Expected 'request/user' to be passed in via context for this serializer")

    class Meta:
        model = Identity
        fields = (
            'provider',
            'identity_uuid',
            'username',
            'project_name',
            'token'
        )
