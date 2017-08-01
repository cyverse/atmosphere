from rest_framework import exceptions, serializers
from api.v2.serializers.summaries import StatusTypeSummarySerializer
from core.models import StatusType


class StatusTypeRelatedField(serializers.RelatedField):

    def get_queryset(self):
        return StatusType.objects.all()

    def to_representation(self, value):
        status_type = StatusType.objects.get(pk=value.pk)
        serializer = StatusTypeSummarySerializer(
            status_type,
            context=self.context)
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
                "StatusType with id '%s' does not exist."
                % identity
            )
