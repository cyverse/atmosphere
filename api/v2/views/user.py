import re

from core.models import AtmosphereUser
from api.permissions import ApiAuthRequired, CloudAdminRequired,\
    InMaintenance
from api.v2.serializers.details import UserSerializer, AdminUserSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup

from rest_framework.filters import SearchFilter
from django.utils import six
from django.db.models import Q
import operator
from functools import reduce

UPDATE_METHODS = ["PUT", "PATCH"]


class MinLengthRequiredSearchFilter(SearchFilter):

    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, 'search_fields', None)
        min_length = getattr(view, 'min_search_length', 1)
        if not search_fields:
            return queryset
        orm_lookups = [self.construct_search(six.text_type(search_field))
                       for search_field in search_fields]
        # NOTE: Moving up 'orm_lookups' to use outside of 'search='
        for idx, _search_field in enumerate(search_fields):
            # Replace "^", "~", and other special characters
            search_field = re.sub('[^A-Za-z0-9]+', '', _search_field)
            if search_field in request.GET:
                search_value = request.GET[search_field]
                query = Q(**{orm_lookups[idx]: search_value})
                queryset = queryset.filter(query)

        #NOTE: This code only executed if 'search=' in request.GET
        for search_term in self.get_search_terms(request):
            # Skip 'search_term' if its  too small to evaluate.
            if len(search_term) < min_length:
                # Forces 0 results if below the requirement.
                queryset = queryset.none()
            or_queries = [Q(**{orm_lookup: search_term})
                          for orm_lookup in orm_lookups]
            reduced_query = reduce(operator.or_, or_queries)
            queryset = queryset.filter(reduced_query).distinct()

        return queryset

    class Meta:
        model = AtmosphereUser
        fields = ["username", "email"]


class UserViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows users to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    max_page_size = 10000
    max_page_size_query_param = 1000
    queryset = AtmosphereUser.objects.all()
    serializer_class = UserSerializer
    filter_backends = (MinLengthRequiredSearchFilter,)
    http_method_names = ['get', 'put', 'patch',
                         'head', 'options', 'trace']
    search_fields = ('^username',)  # NOTE: ^ == Startswith searching

    def get_serializer_class(self):
        if self.request.method in UPDATE_METHODS or \
                (self.request.user.is_staff or self.request.user.is_superuser):
            return AdminUserSerializer
        return self.serializer_class

    def get_permissions(self):
        # Read-only for authenticated users
        if self.request.method is "":
            self.permission_classes = (ApiAuthRequired,
                                       InMaintenance,)
        # CloudAdmin required for PUT/PATCH
        if self.request.method in UPDATE_METHODS:
            self.permission_classes = (CloudAdminRequired,
                                       InMaintenance,)
        return super(UserViewSet, self).get_permissions()
