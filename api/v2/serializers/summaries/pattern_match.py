from rest_framework import serializers

from core.models.pattern_match import PatternMatch, MatchType


class PatternMatchSummarySerializer(serializers.HyperlinkedModelSerializer):
    type = serializers.SlugRelatedField(
        queryset=MatchType.objects.all(),
        slug_field='name')
    url = serializers.HyperlinkedIdentityField(
        view_name='api:v2:patternmatch-detail',
    )

    class Meta:
        model = PatternMatch
        fields = ('id', 'url', 'pattern', 'type')
