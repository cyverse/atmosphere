import factory

from core.models import AccountProvider
from .identity_factory import IdentityFactory
from .provider_factory import ProviderFactory

class AccountProviderFactory(factory.DjangoModelFactory):
    class Meta:
        django_get_or_create = ("provider",)
        model = AccountProvider

    provider = factory.SubFactory(ProviderFactory)
    identity = factory.SubFactory(IdentityFactory)





