from core.models import Credential
from rest_framework import serializers

from urlparse import urlparse

from api.v2.serializers.summaries import IdentitySummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class CredentialSerializer(serializers.HyperlinkedModelSerializer):
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:credential-detail',
    )
    identity = IdentitySummarySerializer(read_only=True)

    def validate_text(self, key, value):
        """
        """
        return value

    def validate_url(self, key, url_value):
        """
        Ensure keys expecting a URL receive a URL
        """
        parse_result = urlparse(url_value)
        if not parse_result.scheme:
            raise serializers.ValidationError("Key: %s expects Valid URL - Value %s throws Error: Missing scheme (http(s)://)" % (key, url_value))
        return url_value

    def validate(self, data):
        # Object-level validation of the key to ensure value 'makes sense' and that only credentials understood by Atmosphere are added.
        if data['key'] in ['admin_url', 'auth_url']:
            self.validate_url(data['key'], data['value'])
        elif data['key'] in ['key', 'secret', 'ex_tenant_name', 'ex_project_name', 'router_name']:
            self.validate_text(data['key'], data['value'])
        else:
            raise serializers.ValidationError(
                "Key %s is not supported as a credential. "
                "Contact a developer for more information."
                % data['key'])
        return data

    class Meta:
        model = Credential
        fields = ('id', 'uuid', 'url', 'identity', 'key', 'value')

