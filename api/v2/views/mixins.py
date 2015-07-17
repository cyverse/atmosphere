import operator

from django.db import models
from django.db.models import Q
from django.http import Http404
from rest_framework.generics import get_object_or_404


class MultipleFieldLookup(object):
    lookup_fields = None

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        #: field to perform lookup with
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        #: kwarg value to lookup
        filter_value = self.kwargs[lookup_url_kwarg]

        #: determine the value of the field
        if isinstance(filter_value, int) or filter_value.isdecimal():
            VALID_FIELDS = (models.AutoField,
                            models.IntegerField,
                            models.BigIntegerField)
        else:
            VALID_FIELDS = (models.UUIDField,
                            models.CharField,
                            models.TextField)

        filter_fields = []
        for field_name in self.lookup_fields:
            try:
                field = queryset.model._meta.get_field(field_name)
            except models.FieldDoesNotExist:
                raise Exception(
                    "The lookup field `%s` does not exist for the model %s."
                    % (field_name, queryset.model.__name__))
            if isinstance(field, VALID_FIELDS):
                filter_fields.append(field_name)

        query_list = [Q(**{f: filter_value}) for f in filter_fields]
        try:
            filter_chain = reduce(operator.or_, query_list)
        except TypeError:
            raise Http404

        obj = get_object_or_404(queryset, filter_chain)
        self.check_object_permissions(self.request, obj)
        return obj
