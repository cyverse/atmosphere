"""
"""
import factory
from factory.django import DjangoModelFactory

from core import models


class AtmosphereUserFactory(DjangoModelFactory):

    class Meta:
        model = models.AtmosphereUser

    email = "test@test.com"
    username = "test"
    password = factory.PostGenerationMethodCall('set_password',
                                                'test')
    is_active = True
    is_staff = True
    is_superuser = True

    # forward dependencies
    selected_identity = factory.SubFactory(
        "core.factories.identity.IdentityFactory")
