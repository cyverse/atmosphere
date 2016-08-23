from rest_framework import serializers

from atmosphere.settings import BLACKLIST_TAGS

from api.v2.serializers.summaries import UserSummarySerializer
from api.v2.serializers.fields.base import UUIDHyperlinkedIdentityField
from core.models import Tag


class TagSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSummarySerializer(read_only=True)
    url = UUIDHyperlinkedIdentityField(
        view_name='api:v2:tag-detail',
    )
    allow_access = serializers.SerializerMethodField()

    def get_allow_access(self, tag):
        tag_name = tag.name.lower()
        return any(tag_name == black_tag.lower()
                   for black_tag in BLACKLIST_TAGS)

    class Meta:
        model = Tag
        fields = (
            'id', 'uuid', 'url', 'name',
            'description', 'user', 'allow_access')
