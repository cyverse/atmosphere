import factory

from core.models import AllocationSource, UserAllocationSource


class AllocationSourceFactory(factory.DjangoModelFactory):
    class Meta:
        model = AllocationSource


class UserAllocationSourceFactory(factory.DjangoModelFactory):
    class Meta:
        model = UserAllocationSource
