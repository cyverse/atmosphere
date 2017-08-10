from rest_framework import exceptions, serializers
from api.v2.serializers.summaries import IdentitySummarySerializer
from core.models import Identity

class IdentityRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return Identity.objects.all()

    def to_representation(self, identity):
        serializer = IdentitySummarySerializer(identity, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identity = data.get("id", None)
        else:
            identity = data
        try:
            return queryset.get(id=identity)
        except:
            raise exceptions.ValidationError(
                "Identity with id '%s' does not exist."
                % identity
            )
