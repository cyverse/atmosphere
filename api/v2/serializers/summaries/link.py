from core.models import ExternalLink
from rest_framework import serializers
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ExternalLinkSummarySerializer(serializers.HyperlinkedModelSerializer):
    # Required when its a uuid -- otherwise LONGINT
    id = serializers.CharField(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:imageversion-detail',
        uuid_field='id'
    )

    class Meta:
        model = ExternalLink
        fields = ('id', 'url', 'title')
