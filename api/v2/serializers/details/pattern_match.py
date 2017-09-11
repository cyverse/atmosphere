from rest_framework import serializers

from api.v2.serializers.fields import ModelRelatedField
from api.v2.serializers.summaries import (
    UserSummarySerializer
)
from core.models.pattern_match import PatternMatch, MatchType
from core.models.user import AtmosphereUser


class PatternMatchSerializer(serializers.HyperlinkedModelSerializer):
    type = serializers.SlugRelatedField(
        queryset=MatchType.objects.all(),
        slug_field='name')
    created_by = ModelRelatedField(
        lookup_field="username",
        default=serializers.CurrentUserDefault(),
        queryset=AtmosphereUser.objects.all(),
        serializer_class=UserSummarySerializer,
        style={'base_template': 'input.html'})
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:patternmatch-detail',
    )

    class Meta:
        model = PatternMatch
        fields = ('id', 'url', 'pattern', 'type', 'created_by')
