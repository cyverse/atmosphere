import factory
import uuid

from core.models import EventTable


class EventTableFactory(factory.DjangoModelFactory):

    class Meta:
        model = EventTable

    uuid = factory.Sequence(lambda n: uuid.uuid4())
