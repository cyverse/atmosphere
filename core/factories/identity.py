"""
"""
from uuid import uuid4

import factory
from factory.django import DjangoModelFactory

from core import models
from core.factories.user import AtmosphereUserFactory
from core.factories.provider import ProviderFactory


class IdentityFactory(DjangoModelFactory):

    class Meta:
        model = models.Identity

    uuid = uuid4()

    # forward dependencies
    created_by = factory.SubFactory(AtmosphereUserFactory)
    provider = factory.SubFactory(ProviderFactory)
