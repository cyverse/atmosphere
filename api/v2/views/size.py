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
        # Switch based on user's ClassType
        if isinstance(request_user, AnonymousUser):
            provider_ids = Provider.objects.filter(only_current(), active=True).values_list('id',flat=True)
        else:
            try:
                group = Group.objects.get(name=request_user.username)
            except Group.DoesNotExist:
                return Size.objects.none()
            provider_ids = group.identities.filter(
                only_current_provider(),
                provider__active=True).values_list('provider', flat=True)

        # Switch based on query
        if 'archived' in self.request.query_params:
            filtered_sizes = Size.objects.filter(
                provider__id__in=provider_ids)
        else:
            filtered_sizes = Size.objects.filter(
                only_current(), provider__id__in=provider_ids)
        return filtered_sizes.filter(~Q(alias='N/A'))
