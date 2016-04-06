"""
    Factory to create Service Provider models in testing
"""
from datetime import datetime
from uuid import uuid4
import pytz

import factory
from factory.django import DjangoModelFactory

from core.models import provider as models
from core.models.instance_action import InstanceAction


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

    uuid = uuid4()
    location = "Tucson, AZ"
    description = "Provider used in testing"
    active = True
    public = True
    start_date = datetime(2015, 1, 1, tzinfo=pytz.UTC)
    end_date = None

    # forward dependencies
    type = factory.SubFactory(ProviderTypeFactory)
    virtualization = factory.SubFactory(PlatformTypeFactory)


class DNSFactory(DjangoModelFactory):

    class Meta:
        model = models.ProviderDNSServerIP

    ip_address = factory.Sequence(lambda n: "%s.%s.%s.%s" % n)
    order = factory.Sequence(lambda n: n)

    # forward dependencies
    provider = factory.SubFactory(ProviderFactory)

# Placed here in order to use "ProviderInstanceAction"
# Move to "Instance" factories when enough classes exist.


class InstanceActionFactory(DjangoModelFactory):

    class Meta:
        model = InstanceAction

    name = factory.Sequence(lambda n: "action-%s" % n)
    description = factory.Sequence(lambda n: "Description for action %s" % n)


class ProviderInstanceActionFactory(DjangoModelFactory):

    class Meta:
        model = models.ProviderInstanceAction
    enabled = True
    instance_action = factory.SubFactory(InstanceActionFactory)
    provider = factory.SubFactory(ProviderFactory)
