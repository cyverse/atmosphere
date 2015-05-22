from core.models.post_boot import BootScript
from rest_framework import serializers
from api.v2.serializers.details import BootScriptSerializer


class ModelRelatedField(serializers.RelatedField):
    model = None
    serializer_class = None

    def get_queryset(self):
        assert self.model is not None, (
            "%s should have a `model` attribute."
            % self.___class__.__name__
        )
        return model.objects.all()

    def to_representation(self, value):
        assert self.serializer_class is not None, (
            "%s should have a `serializer_class` attribute."
            % self.___class__.__name__
        )
        queryset = self.get_queryset()
        instance = queryset.get(pk=value.pk)
        serializer = serializer_class(instance, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        if isinstance(data, dict):
            instance_id = data.get("id", None)
        else:
            instance_id = data
        try:
            return queryset.get(id=instance_id)
        except:
            raise exceptions.ValidationError(
                "%s with id '%s' does not exist."
                % (self.model.__class__.__name__, identity)
            )


class BootScriptRelatedField(ModelRelatedField):
    model = BootScript
    serializer_class = BootScriptSerializer

    def get_queryset(self):
        return BootScript.objects.all()

    def to_representation(self, value):
        script = BootScript.objects.get(id=value)
        serializer = BootScriptSerializer(script, context=self.context)
        return serializer.data

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        self.data
