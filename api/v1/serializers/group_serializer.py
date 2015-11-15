from core.models.group import Group
from rest_framework import serializers


class GroupSerializer(serializers.ModelSerializer):
    identities = serializers.SerializerMethodField('get_identities')

    class Meta:
        model = Group
        exclude = ('id', 'providers')

    def get_identities(self, group):
        identities = group.current_identities.all()
        return map(lambda i:
                   {"id": i.uuid, "provider_id": i.provider.uuid},
                   identities)
