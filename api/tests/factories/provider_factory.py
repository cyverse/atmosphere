import factory
from factory import fuzzy

from core.models import Provider, AccountProvider
from .provider_type_factory import ProviderTypeFactory
from .platform_type_factory import PlatformTypeFactory


class ProviderFactory(factory.DjangoModelFactory):

    class Meta:
        django_get_or_create = ("location",)
        model = Provider

    type = factory.SubFactory(ProviderTypeFactory)
    virtualization = factory.SubFactory(PlatformTypeFactory)
    location = fuzzy.FuzzyChoice(["Marana", "Tombstone"])
    cloud_config = { "network": { "topology": "External Router Topology" } }

    @factory.post_generation
    def create_admin_identity(provider, *args, **kwargs):
        from .account_provider_factory import AccountProviderFactory
        from .identity_factory import IdentityFactory
        from .user_factory import UserFactory
        user = UserFactory.create(username="admin")
        admin_ident = IdentityFactory.create(provider=provider, created_by=user)
        AccountProviderFactory.create(provider=provider, identity=admin_ident)

    @factory.post_generation
    def create_provider_creds(provider, *args, **kwargs):
        provider.providercredential_set.create(key="public_routers", value="mock-router1")
        provider.providercredential_set.create(key="router_name", value="mock-router")
