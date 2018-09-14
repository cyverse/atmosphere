import factory
import uuid
from core.models import InstanceSource
from .provider_factory import ProviderFactory


class InstanceSourceFactory(factory.DjangoModelFactory):
    class Meta:
        model = InstanceSource

    identifier = factory.Sequence(lambda n: uuid.uuid4())
    provider = factory.SubFactory(ProviderFactory)
