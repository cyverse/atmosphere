from core.models.group import IdentityMembership
from rest_framework import serializers


class AccountSerializer(serializers.ModelSerializer):
    credentials = serializers.ReadOnlyField(source='identity.get_credentials')
    identity_id = serializers.ReadOnlyField(source='identity.uuid')
    provider_id = serializers.ReadOnlyField(source='identity.provider_uuid')
    group_name = serializers.ReadOnlyField(source='member.name')

    class Meta:
        model = IdentityMembership
        fields = ('identity_id', 'credentials', 'provider_id', 'group_name')


class POST_AccountSerializer(serializers.Serializer):

    """
TODO: Decide how a CloudAdmin could programmatically add a new account to atmosphere..
Example Input:
{
    "credentials": {"key":"..",
                    "secret":"..",
                    "ex_project_name":".."},
    "group_name": "sgregory",
    "identity": <creaated from credentials>,
    "provider": <dirived from CloudAdmin>,
}
    """
    pass

    class Meta:
        fields = ('', '')
