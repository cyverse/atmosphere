from django.utils import timezone
import factory
from api.tests.factories.user_factory import UserFactory

from core.models import AllocationSource, UserAllocationSource


class AllocationSourceFactory(factory.DjangoModelFactory):
    name = factory.fuzzy.FuzzyText()
    compute_allowed = 168
    start_date = factory.fuzzy.FuzzyDateTime(timezone.now())
    end_date = None
    renewal_strategy = "default"

    class Meta:
        model = AllocationSource


class UserAllocationSourceFactory(factory.DjangoModelFactory):
    allocation_source = factory.SubFactory(AllocationSourceFactory)
    user = factory.SubFactory(UserFactory)
    class Meta:
        model = UserAllocationSource
