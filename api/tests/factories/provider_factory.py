import factory
from core.models import Provider
from .provider_type_factory import ProviderTypeFactory
from .platform_type_factory import PlatformTypeFactory


class ProviderFactory(factory.DjangoModelFactory):

    class Meta:
        model = Provider

    type = factory.SubFactory(ProviderTypeFactory)
    virtualization = factory.SubFactory(PlatformTypeFactory)
