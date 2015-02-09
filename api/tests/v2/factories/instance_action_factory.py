import factory
from core.models import InstanceAction


class InstanceActionFactory(factory.DjangoModelFactory):
    class Meta:
        model = InstanceAction
