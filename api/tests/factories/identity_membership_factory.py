import factory
from core.models import IdentityMembership


class IdentityMembershipFactory(factory.DjangoModelFactory):

    class Meta:
        model = IdentityMembership
