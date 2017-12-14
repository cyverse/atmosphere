import factory
from core.models import EventTable


class EventTableFactory(factory.DjangoModelFactory):

    class Meta:
        model = EventTable
