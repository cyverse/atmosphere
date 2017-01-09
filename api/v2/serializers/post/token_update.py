from core.models import (
    AtmosphereUser, Identity
)
from core.query import only_current, contains_credential
from api.v2.serializers.details.credential import CredentialSerializer
from service.driver import get_esh_driver, get_account_driver
from rtwo.exceptions import KeystoneUnauthorized

from rest_framework import serializers


class TokenUpdateSerializer(serializers.Serializer):
    """
    """
    # Flags
    new_token = serializers.CharField(write_only=True)

    def validate(self, data):
        """
        Validation will:
        - Ensure that user/group exists (Or create it)
        - 
        """
        validated_data = data
        self.validate_new_token(data['new_token'])
        return validated_data

    def create(self, validated_data):
        #FIXME: Set the user's respective Identities appropriately.
        raise Exception("Create method not finished")

    def validate_driver(self, validated_data):
        request_user = self._get_request_user()
        raise serializers.ValidationError("Attempting to create a driver for user %s failed. Message: %s" % (request_user.username, "validate_driver method incomplete"))

    def validate_new_token(self, new_token_key):
        request_user = self._get_request_user()
        #TODO: Create a driver, setting this as the new token. Verify you can access a call via driver, *ELSE* throw a ValidationError (token returned was unable to create a rtwo driver!)
        raise serializers.ValidationError("validate_new_token Method incomplete")

    class Meta:
        fields = (
            'provider',
            'username',
            'new_token'
        )


def validate_identity(new_identity):
    try:
        driver = get_esh_driver(new_identity)
        driver.list_sizes()
    except:
        new_identity.delete()
        raise # Exception("The driver created by this identity was invalid")
