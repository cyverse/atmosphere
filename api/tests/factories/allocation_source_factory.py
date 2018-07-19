import factory

from core.models import AllocationSource, UserAllocationSource


class AllocationSourceFactory(factory.DjangoModelFactory):
    class Meta:
        model = AllocationSource

    compute_allowed = 168


class UserAllocationSourceFactory(factory.DjangoModelFactory):
    class Meta:
        model = UserAllocationSource
