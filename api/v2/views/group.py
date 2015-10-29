import operator
from functools import reduce

from django.utils import six
from django.db.models import Q

from rest_framework.filters import SearchFilter
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from api.v2.serializers.details import GroupSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup
from api.v2.exceptions import failure_response
from core.models import AtmosphereUser, Group


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


class GroupViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows groups to be viewed or edited.
    """

    lookup_fields = ("id", "uuid")
    max_page_size = 10000
    max_page_size_query_param = 1000
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_backends = (MinLengthRequiredSearchFilter,)
    http_method_names = ['get', 'post', 'head', 'options', 'trace']
    search_fields = ('^groupname',)  # NOTE: ^ == Startswith searching

    def lookup_group(self, key):
        """
        Find group based on UUID or ID/PK
        """
        if type(key) == int:
            group = Group.objects.filter(pk=key)
        else:
            group = Group.objects.filter(uuid=key)
        if not group:
            return None
        return group[0]

    @detail_route(methods=['post'])
    def add_user(self, request, pk=None):
        group = self.lookup_group(pk)
        data = request.data
        add_user = data.pop('username')
        user = AtmosphereUser.objects.filter(username=add_user)
        if not user.count():
            return failure_response(409, "Username %s does not exist" % add_user)
        user = user[0]
        group.user_set.add(user)
        serialized_data = GroupSerializer(group, context={'request': request}).data
        return Response(serialized_data)

    @detail_route(methods=['post'])
    def remove_user(self, request, pk=None):
        group = self.lookup_group(pk)
        data = request.data
        del_user = data.pop('username')
        user = AtmosphereUser.objects.filter(username=del_user)
        if not user.count():
            return failure_response(409, "Username %s does not exist" % del_user)
        user = user[0]
        group.user_set.remove(user)
        serialized_data = GroupSerializer(group, context={'request': request}).data
        return Response(serialized_data)
