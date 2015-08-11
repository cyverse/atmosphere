from django.contrib.auth.models import AnonymousUser

from core.models import Group, Size, Provider
from core.query import only_current, only_current_provider

from api.v2.serializers.details import SizeSerializer
from api.v2.views.base import AuthReadOnlyViewSet


class SizeViewSet(AuthReadOnlyViewSet):

    """
    API endpoint that allows instance actions to be viewed or edited.
    """

    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    filter_fields = ('provider__id',)

    def get_queryset(self):
        """
        Filter projects by current user
        """
        user = self.request.user
        # Switch based on user type
        if isinstance(request_user, AnonymousUser):
            provider_ids = Provider.objects.filter(only_current(), active=True).values_list('id',flat=True)
        else:
            group = Group.objects.get(name=user.username)
            provider_ids = group.identities.filter(
                only_current_provider(),
                provider__active=True).values_list('provider', flat=True)

        # Switch based on query
        if 'archived' in self.request.QUERY_PARAMS:
            return Size.objects.filter(
                provider__id__in=provider_ids)
        else:
            return Size.objects.filter(
                only_current(), provider__id__in=provider_ids)
