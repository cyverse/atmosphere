import factory

import core.models
from core.models.instance_history import InstanceStatusHistory, InstanceStatus


class InstanceStatusFactory(factory.DjangoModelFactory):
    class Meta:
        model = InstanceStatus


class InstanceSizeFactory(factory.DjangoModelFactory):
    class Meta:
        model = core.models.Size


class InstanceHistoryFactory(factory.DjangoModelFactory):
    class Meta:
        model = InstanceStatusHistory

    status = factory.SubFactory(InstanceStatusFactory)
