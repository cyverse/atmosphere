"""
"""
import factory
from factory.django import DjangoModelFactory

from core import models
from core.factories.identity import IdentityFactory
from core.factories.provider import ProviderFactory


class AccountProviderFactory(DjangoModelFactory):

    class Meta:
        model = models.AccountProvider

    provider = factory.SubFactory(ProviderFactory)
    identity = factory.SubFactory(IdentityFactory)
