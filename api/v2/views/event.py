import django_filters

from core.models import EventTable
from api.v2.serializers.details import EventSerializer
from api.v2.views.base import AuthViewSet
from api.v2.views.mixins import MultipleFieldLookup


class EventFilter(django_filters.FilterSet):
    class Meta:
        model = EventTable
        fields = ['entity_id', 'name']


class EventViewSet(MultipleFieldLookup, AuthViewSet):

    """
    API endpoint that allows scripts to be viewed or edited.
    """

    queryset = EventTable.objects.none()
    serializer_class = EventSerializer
    filter_class = EventFilter
    search_fields = ('^name',)
    lookup_fields = ('id', 'uuid')
    http_method_names = ['options','head','post']
