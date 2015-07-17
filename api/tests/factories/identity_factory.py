import factory
from core.models import Identity


class IdentityFactory(factory.DjangoModelFactory):

    class Meta:
        model = Identity
