from rest_framework import serializers
from rest_framework import exceptions

# from api.v2.serializers.summaries import BootScriptSummarySerializer
# from core.models.post_boot import BootScript


class ModelRelatedField(serializers.RelatedField):
    """
    Related field that renders view based on `serializer_class`
    """
    lookup_field = "id"

    model = None

    serializer_class = None

    def get_queryset(self):
        assert self.model is not None, (
            "%s should have a `model` attribute."
            % self.___class__.__name__
        )
        return self.model.objects.all()

    def to_representation(self, value):
        assert self.serializer_class is not None, (
            "%s should have a `serializer_class` attribute."
            % self.___class__.__name__
        )
        queryset = self.get_queryset()
        obj = queryset.get(pk=value.pk)
        serializer = self.serializer_class(obj, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            identifier = data.get(self.lookup_field, None)
        else:
            identifier = data
        try:
            return queryset.get(**{self.lookup_field: identifier})
        except:
            raise exceptions.ValidationError(
                "%s with id '%s' does not exist."
                % (self.model.__class__.__name__, identifier)
            )


# class BootScriptRelatedField(ModelRelatedField):
#     model = BootScript
#     serializer_class = BootScriptSummarySerializer
#
#     def get_queryset(self):
#         return BootScript.objects.all()
#
#     def to_representation(self, value):
#         script = BootScript.objects.get(id=value)
#         serializer = BootScriptSerializer(script, context=self.context)
#         return serializer.data
#
#     def to_internal_value(self, data):
#         queryset = self.get_queryset()
#         self.data
