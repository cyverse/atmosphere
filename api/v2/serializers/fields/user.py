from core.models import AtmosphereUser
from rest_framework import serializers
from api.v2.serializers.summaries import UserSummarySerializer


class UserRelatedField(serializers.RelatedField):

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super(UserRelatedField, self).__init__(**kwargs)

    def to_representation(self, value):
        username = value.__str__()
        user = AtmosphereUser.objects.get(username=username)
        serializer = UserSummarySerializer(user, context=self.context)
        return serializer.data
