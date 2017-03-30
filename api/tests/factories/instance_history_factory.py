import factory
from core.models.instance_history import InstanceStatusHistory, InstanceStatus


class InstanceStatusFactory(factory.DjangoModelFactory):

    class Meta:
        model = InstanceStatus


class InstanceHistoryFactory(factory.DjangoModelFactory):

    class Meta:
        model = InstanceStatusHistory

    status = factory.SubFactory(InstanceStatusFactory)
