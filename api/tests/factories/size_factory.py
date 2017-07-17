import factory

from core.models import Size

from .provider_factory import ProviderFactory


class SizeFactory(factory.DjangoModelFactory):

    class Meta:
        model = Size

    alias = factory.Sequence(lambda n: 'size_alias%d' % n)
    name = factory.Sequence(lambda n: 'size%d' % n)
    cpu = 1
    disk= 0
    root= 0
    mem= 1
    provider = factory.SubFactory(ProviderFactory)
