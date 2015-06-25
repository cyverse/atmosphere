from core.models import AtmosphereUser
from api.v2.serializers.details import UserSerializer
from api.v2.views.base import AuthViewSet

from rest_framework.filters import SearchFilter
from django.utils import six
from django.db.models import Q
import operator


class MinLengthRequiredSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, 'search_fields', None)
        min_length = getattr(view, 'min_search_length', 1)
        if not search_fields:
            return queryset
        orm_lookups = [self.construct_search(six.text_type(search_field))
                       for search_field in search_fields]
        for search_term in self.get_search_terms(request):
            #Skip 'search_term' if its  too small to evaluate.
            if len(search_term) < min_length:
                #Forces 0 results if below the requirement.
                queryset = queryset.none()
            or_queries = [Q(**{orm_lookup: search_term})
                          for orm_lookup in orm_lookups]
            reduced_query = reduce(operator.or_, or_queries)
            queryset = queryset.filter(reduced_query).distinct()
        return queryset
    class Meta:
        model = AtmosphereUser
        fields = ["username", "email"]


class UserViewSet(AuthViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = AtmosphereUser.objects.all()
    serializer_class = UserSerializer
    filter_backends = (MinLengthRequiredSearchFilter,)
    http_method_names = ['get', 'head', 'options', 'trace']
    search_fields = ('^username',)  # NOTE: ^ == Startswith searching
