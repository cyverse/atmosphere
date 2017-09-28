import operator
from functools import reduce

from django.utils import six
from django.db.models import Q

from rest_framework.filters import SearchFilter, DjangoFilterBackend
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework import filters
import django_filters

from api.v2.serializers.details import GroupSerializer
from api.v2.views.base import AuthModelViewSet
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


class GroupFilter(filters.FilterSet):
    identity_id = django_filters.CharFilter('identity_memberships__identity__id')
    identity_uuid = django_filters.CharFilter('identity_memberships__identity__uuid')
    name = django_filters.CharFilter('name', lookup_expr=['contains', 'startswith'])
    #is_private = django_filters.FilterMethod(method='is_private')

    def is_private(self):
        """
        For now, this is how we can verify if the group is 'private'.
        Later, we might have to remove the property and include a 'context user'
        so that we can determine the ownership (of the group, or that the name is a perfect match, etc.)
        """
        return self.leaders.count() == 1

    class Meta:
        model = Group
        fields = ["identity_id", "identity_uuid", "name"]

class GroupViewSet(MultipleFieldLookup, AuthModelViewSet):

    """
    API endpoint that allows groups to be viewed or edited.
    """

    lookup_fields = ("id", "uuid")
    max_page_size = 10000
    max_page_size_query_param = 1000
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_backends = (DjangoFilterBackend, MinLengthRequiredSearchFilter)
    filter_class = GroupFilter
    http_method_names = ['get', 'post', 'patch', 'head', 'options', 'trace']
    search_fields = ('^name',)  # NOTE: ^ == Startswith searching

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

    def get_queryset(self):
        """
        Filter out tags for deleted instances
        """
        # Staff users are allowed to manipulate groups they are not in,
        #  To make it easier to distinguish GET calls need to include ?admin=true
        if self.request.user.is_staff and (
                'admin' in self.request.query_params or
                self.request._request.method != 'GET'
                ):
            return Group.objects.all()
        # Allow non-staff users to search the group API, useful for GUI experience
        # NOTE: In the project-sharing, user-group-mapping future,
        # this could be removed so that users can only
        # add members who are in the same group...
        if 'search' in self.request.query_params and self.request._request.method == 'GET':
            return Group.objects.all()
        user_id = self.request.user.id
        return Group.objects.filter(memberships__user__id=user_id)
