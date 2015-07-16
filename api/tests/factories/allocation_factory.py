import factory
from core.models import Allocation


class AllocationFactory(factory.DjangoModelFactory):

    class Meta:
        model = Allocation
