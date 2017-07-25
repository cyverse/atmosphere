import factory

import core.models
from core.models.instance_history import InstanceStatusHistory
from .size_factory import SizeFactory


class InstanceStatusFactory(factory.DjangoModelFactory):
    class Meta:
        model = core.models.InstanceStatus


class InstanceHistoryFactory(factory.DjangoModelFactory):
    class Meta:
        model = InstanceStatusHistory

    status = factory.SubFactory(InstanceStatusFactory)
    size = factory.SubFactory(SizeFactory)
