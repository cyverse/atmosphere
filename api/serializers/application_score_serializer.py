from core.models.application import ApplicationScore
from rest_framework import serializers


class ApplicationScoreSerializer(serializers.ModelSerializer):
    """
    """
    #TODO:Need to validate provider/identity membership on id change
    username = serializers.CharField(read_only=True, source='user.username')
    application = serializers.CharField(read_only=True,
                                        source='application.name')
    vote = serializers.CharField(read_only=True, source='get_vote_name')

    class Meta:
        model = ApplicationScore
        fields = ('username', "application", "vote")