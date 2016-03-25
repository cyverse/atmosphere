from rest_framework import filters
import django_filters

from api import permissions
from api.v2.serializers.details import ImageSerializer
from api.v2.views.base import AuthOptionalViewSet
from api.v2.views.mixins import MultipleFieldLookup

from core.models import Application as Image


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
        return Image.current_apps(request_user)
