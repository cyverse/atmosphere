import factory
from core.models import ProviderMembership


class ProviderMembershipFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProviderMembership
