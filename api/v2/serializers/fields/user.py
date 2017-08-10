from core.models import AtmosphereUser
from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer


class UserRelatedField(serializers.RelatedField):

    def to_representation(self, user):
        serializer = UserSummarySerializer(user, context=self.context)
        return serializer.data
