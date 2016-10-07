from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from core.models import Group, Size, Provider
from core.query import only_current, only_current_provider

from api.v2.serializers.details import SizeSerializer
from api.v2.views.base import AuthReadOnlyViewSet
from api.v2.views.mixins import MultipleFieldLookup


class SizeViewSet(MultipleFieldLookup, AuthReadOnlyViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Size.objects.all().order_by('-cpu','-mem')
    serializer_class = SizeSerializer
    ordering = ("cpu", "mem", "disk", "root", "name")
    filter_fields = ('provider__id',)

    def get_queryset(self):
        """
        Filter projects by current user
        """
        request_user = self.request.user
        providers = request_user.current_providers

        # Switch based on query
        if 'archived' in self.request.query_params:
            filtered_sizes = Size.objects.filter(
                provider__in=providers)
        else:
            filtered_sizes = Size.objects.filter(
                only_current(),
                provider__in=providers)
        return filtered_sizes.filter(~Q(alias='N/A'))
