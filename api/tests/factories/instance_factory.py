import factory
from core.models import Instance


class InstanceFactory(factory.DjangoModelFactory):

    class Meta:
        model = Instance
