import factory
from core.models import ProviderType


class ProviderTypeFactory(factory.DjangoModelFactory):

    class Meta:
        model = ProviderType
