from rest_framework import serializers
from rest_framework import exceptions
from django.core.exceptions import ObjectDoesNotExist
from django.db import ProgrammingError


class ModelRelatedField(serializers.RelatedField):
    """
    Related field that renders the representation based on `serializer_class`
    and converts to an internal representation using `lookup_field`.
    """
    lookup_field = "pk"

    def __init__(self, *args, **kwargs):
        self.serializer_class = kwargs.pop("serializer_class")
        self.lookup_field = kwargs.pop("lookup_field", self.lookup_field)
        super(ModelRelatedField, self).__init__(*args, **kwargs)

    def get_queryset(self):
        assert self.queryset is not None, (
            "%s should have a `queryset` attribute."
            % self.___class__.__name__
        )
        if callable(self.queryset):
            return self.queryset(self)

        return self.queryset.all()

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
        except (TypeError, ValueError,
                ProgrammingError, ObjectDoesNotExist):
            raise exceptions.ValidationError(
                "%s with Field: %s '%s' does not exist."
                % (self.queryset.model.__name__, self.lookup_field, identifier)
            )
