from django.contrib.auth.models import AnonymousUser
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter

from core.models import ExternalLink as ExternalLink
from api.v2.views.base import AuthOptionalViewSet
from api.v2.serializers.details import ExternalLinkSerializer


class LinkFilter(filters.FilterSet):
    image_id = filters.CharFilter('application__id')
    created_by = filters.CharFilter('application__created_by__username')

    class Meta:
        model = ExternalLink
        fields = ['image_id', 'created_by']


class ExternalLinkViewSet(AuthOptionalViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    queryset = ExternalLink.objects.all()
    serializer_class = ExternalLinkSerializer
    search_fields = ('created_by__username')
    filter_class = LinkFilter
    filter_backends = (OrderingFilter, filters.DjangoFilterBackend)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        request_user = self.request.user
        if type(request_user) == AnonymousUser:
            return ExternalLink.objects.none()
        return ExternalLink.objects.filter(created_by=request_user)
