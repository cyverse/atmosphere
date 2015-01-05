"""
    Factory to create Service Provider models in testing
"""
from datetime import datetime
from uuid import uuid4
import pytz

import factory
from factory.django import DjangoModelFactory

from core.models import provider as models


class TraitFactory(DjangoModelFactory):
    class Meta:
        model = models.Trait

    name = factory.Sequence(lambda n: "trait-%s" % n)
    description = factory.Sequence(lambda n: "Description for trait %s" % n)


class PlatformTypeFactory(DjangoModelFactory):
    class Meta:
        model = models.PlatformType

    name = "test-platform"


class ProviderTypeFactory(DjangoModelFactory):
    class Meta:
        model = models.ProviderType

    name = factory.Sequence(lambda n: "Provider Type %s" % n)
    start_date = datetime(2015, 1, 1, tzinfo=pytz.UTC)
    end_date = datetime(2015, 1, 3, tzinfo=pytz.UTC)


class ProviderFactory(DjangoModelFactory):
    class Meta:
        model = models.Provider

    uuid = str(uuid4())
    location = "Tucson, AZ"
    description = "Provider used in testing"
    active = True
    public = True
    start_date = datetime(2015, 1, 1, tzinfo=pytz.UTC)
    end_date = None

    # forward dependencies
    type = factory.SubFactory(ProviderTypeFactory)
    virtualization = factory.SubFactory(PlatformTypeFactory)

    @factory.post_generation
    def traits(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for trait in extracted:
                self.traits.add(trait)
