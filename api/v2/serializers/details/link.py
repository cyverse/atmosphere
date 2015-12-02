from core.models import ExternalLink
from rest_framework import serializers

from api.v2.serializers.summaries import UserSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField


class ExternalLinkSerializer(serializers.HyperlinkedModelSerializer):
    created_by = UserSummarySerializer(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:externallink-detail',
        uuid_field='id'
    )

    class Meta:
        model = ExternalLink
        fields = (
            'id',
            'url',
            'title',
            'description',
            'link',
            # Adtl. Fields
            'created_by'
        )
