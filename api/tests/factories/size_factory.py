import factory
from core.models import Size


class SizeFactory(factory.DjangoModelFactory):

    class Meta:
        model = Size

    alias = factory.Sequence(lambda n: 'size_alias%d' % n)
    name = factory.Sequence(lambda n: 'size%d' % n)
