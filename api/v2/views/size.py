from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
import django_filters

from core.models import Group, Size, Provider, ProviderMachine
from core.query import only_current, only_current_provider

from api.v2.serializers.details import SizeSerializer
from api.v2.views.base import AuthReadOnlyViewSet
from api.v2.views.mixins import MultipleFieldLookup

class SizeFilter(django_filters.FilterSet):
    provider_machine__id = django_filters.filters.CharFilter(method='filter_provider_machine')

    def filter_provider_machine(self, qs, name, value):
        selected_machine = ProviderMachine.objects.filter(
            Q(id=value)
            | Q(instance_source__identifier=value)).first()
        size_threshold = selected_machine.instance_source.size_gb
        return qs.filter(
            Q(disk=0)
            | Q(disk__gt=size_threshold))

    class Meta:
        model = Size
        fields = ['provider__id', 'provider_machine__id']

class SizeViewSet(MultipleFieldLookup, AuthReadOnlyViewSet):
    """
    API endpoint that allows instance actions to be viewed or edited.
    """
    lookup_fields = ("id", "uuid")
    queryset = Size.objects.all().order_by('-disk','-cpu','-mem')
    serializer_class = SizeSerializer
    ordering = ("disk", "cpu", "mem", "root", "name")
    filter_class = SizeFilter

    def get_queryset(self):
        """
        Filter projects by current user
        """
        request_user = self.request.user
        # Switch based on user's ClassType
        if isinstance(request_user, AnonymousUser):
            providers = Provider.objects.filter(only_current(), active=True)
        else:
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
