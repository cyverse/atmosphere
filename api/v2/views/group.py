import operator
from functools import reduce

from django.utils import six
from django.db.models import Q

from rest_framework.filters import SearchFilter
from rest_framework.decorators import detail_route

from api.v2.serializers.details import MembershipSerializer
from api.v2.views.base import AuthViewSet
from core.models import Group


class MinLengthRequiredSearchFilter(SearchFilter):

    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, 'search_fields', None)
        min_length = getattr(view, 'min_search_length', 1)
        if not search_fields:
            return queryset
        orm_lookups = [self.construct_search(six.text_type(search_field))
                       for search_field in search_fields]
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
        model = Group
        fields = ["name", "user_set__email"]


class MembershipViewSet(AuthViewSet):

    """
    API endpoint that allows groups to be viewed or edited.
    """

    max_page_size = 10000
    max_page_size_query_param = 1000
    queryset = Group.objects.all()
    serializer_class = MembershipSerializer
    filter_backends = (MinLengthRequiredSearchFilter,)
    http_method_names = ['get', 'post', 'head', 'options', 'trace']
    search_fields = ('^groupname',)  # NOTE: ^ == Startswith searching

    @detail_route(methods=['get'])
    def users(self, request, pk=None):
        group = Group.objects.get(pk=pk)

