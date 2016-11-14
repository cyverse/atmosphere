from core.models import ProviderCredential
from rest_framework import serializers

from urlparse import urlparse


class ProviderCredentialSerializer(serializers.ModelSerializer):

    def validate_version(self, key, value):
        """
        Ensure version is 'valid'
        """
        if value not in ['2.0_password', '3.x_password']:
            raise serializers.ValidationError("Key: %s - value represents an invalid version" % key)
        return value

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
            raise serializers.ValidationError(
                "Key: %s expects Valid URL - Value %s throws Error: "
                "Missing scheme (http(s)://)" % (key, url_value))
        return url_value

    def validate(self, data):
        """
        Object-level validation of the key to ensure value 'makes sense'
        and that only credentials understood by Atmosphere are added.
        """
        if data['key'] in ['admin_url', 'auth_url']:
            self.validate_url(data['key'], data['value'])
        elif data['key'] in ['public_routers', 'network_name', 'router_name', 'region_name', 'domain_name']:
            self.validate_text(data['key'], data['value'])
        elif data['key'] in ['ex_force_auth_version']:
            self.validate_version(data['key'], data['value'])
        else:
            raise serializers.ValidationError(
                "Key %s is not supported as a ProviderCredential. "
                "Contact a developer for more information."
                % data['key'])
        return data

    class Meta:
        model = ProviderCredential
        fields = ('id', 'uuid', 'key', 'value')
