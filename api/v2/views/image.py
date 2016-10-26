from rest_framework import filters
import django_filters

from api import permissions
from api.v2.serializers.details import ImageSerializer
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup

from core.models import Application as Image


#
# The following imports and method and monkey patch are a quick fix for a big
# problem.  The patch should be removed when the equivalent drf method does
# not chain filter methods. Chaining filter methods with m2m relations,
# can result in /very/ bad performance. For more information see:
#
#   https://code.djangoproject.com/ticket/27303#comment:26
#
from django.utils import six; from django.db import models; import operator
def filter_queryset(self, request, queryset, view):
    search_fields = getattr(view, 'search_fields', None)
    search_terms = self.get_search_terms(request)

    if not search_fields or not search_terms:
        return queryset

    orm_lookups = [
        self.construct_search(six.text_type(search_field))
        for search_field in search_fields
    ]

    conditions = []
    for search_term in search_terms:
        queries = [
            models.Q(**{orm_lookup: search_term})
            for orm_lookup in orm_lookups
        ]
        conditions.append(reduce(operator.or_, queries))

    return queryset.filter(reduce(operator.and_, conditions)).distinct()

filters.SearchFilter.filter_queryset = filter_queryset

class ImageFilter(filters.FilterSet):
    created_by = django_filters.CharFilter('created_by__username')
    project_id = django_filters.CharFilter('projects__uuid')
    tag_name = django_filters.CharFilter('tags__name')
    # Legacy filters
    created_by__username = django_filters.CharFilter('created_by__username')
    projects__id = django_filters.CharFilter('projects__id')
    tags__name = django_filters.CharFilter('tags__name')

    class Meta:
        model = Image
        fields = ['tag_name', 'project_id', 'created_by',
                  'created_by__username', 'tags__name', 'projects__id']

class BookmarkedFilterBackend(filters.BaseFilterBackend):
    """
    Filter bookmarks when 'favorited' is set
    """
    def filter_queryset(self, request, queryset, view):
        request_user = request.user
        request_params = request.query_params
        bookmarked = request_params.get('bookmarked')
        if isinstance(bookmarked, basestring) and bookmarked.lower() == 'true'\
                or isinstance(bookmarked, bool) and bookmarked:
            return queryset.filter(bookmarks__user=request_user)

        return queryset


class ImageViewSet(MultipleFieldLookup, AuthOptionalViewSet):

    """
    API endpoint that allows images to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    http_method_names = ['get', 'put', 'patch', 'head', 'options', 'trace']
    permission_classes = (permissions.InMaintenance,
                          permissions.ApiAuthOptional,
                          permissions.CanEditOrReadOnly,
                          permissions.ApplicationMemberOrReadOnly)

    serializer_class = ImageSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.SearchFilter, BookmarkedFilterBackend)
    filter_class = ImageFilter
    search_fields = ('id', 'name', 'versions__change_log', 'tags__name',
                     'tags__description', 'created_by__username',
                     'versions__machines__instance_source__identifier',
                     'versions__machines__instance_source__provider__location')

    def get_queryset(self):
        request_user = self.request.user
        return Image.images_for_user(request_user)
