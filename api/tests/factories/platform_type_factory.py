import factory
from core.models import PlatformType


class PlatformTypeFactory(factory.DjangoModelFactory):

    class Meta:
        model = PlatformType
