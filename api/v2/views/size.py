from rest_framework import viewsets
from core.models import Group, Size
from api.v2.serializers.details import SizeSerializer
from core.query import only_current


class SizeViewSet(viewsets.ReadOnlyModelViewSet):
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
        group = Group.objects.get(name=user.username)
        providers = group.providers.filter(only_current(), active=True)
        return Size.objects.filter(only_current(), provider__in=providers)
