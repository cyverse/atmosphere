import operator

from django.db import models
from django.db.models import Q
from django.http import Http404
from rest_framework.generics import get_object_or_404


class MultipleFieldLookup(object):
    lookup_fields = None

    def get_object(self):
        # NOTE: 'distinct()' required to avoid failing on AnonymousUser access
        # specifically, in the 'v2/images/##' URL endpoint
        queryset = self.filter_queryset(self.get_queryset()).distinct()
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

        assert self.lookup_fields is not None, (
            "%s must define the attribute `lookup_fields`."
            % self.__class__.__name__
        )

        filter_fields = []
        for field_name in self.lookup_fields:
            try:
                if '.' not in field_name and '__' not in field_name:
                    field = queryset.model._meta.get_field(field_name)
                else:
                    #NOTE: This allows for 'x__y' or 'x.y' support
                    field_split_list = field_name.replace('__','.').split('.')
                    field = queryset.model._meta.get_field(field_split_list[0])
                    for n_field in field_split_list[1:]:
                        field = field.related_model._meta.get_field(n_field)
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
