import factory

import core.models
from core.models.instance_history import InstanceStatusHistory, InstanceStatus
from .size_factory import SizeFactory


class InstanceStatusFactory(factory.DjangoModelFactory):
    class Meta:
        model = core.models.InstanceStatus


class InstanceHistoryFactory(factory.DjangoModelFactory):
    # status is a LazyAttribute to allow for the convenience of constructing
    # histories with a single word status, rather than a separate
    # InstanceStatus. They can be created like so
    # InstanceStatusFactory.create(status_name="active")
    status = factory.LazyAttribute(lambda o: \
            InstanceStatus.objects.get_or_create(name=o.status_name)[0])
    size = factory.SubFactory(SizeFactory)

    @factory.lazy_attribute
    def version(self):
        ish = InstanceStatusHistory.objects.filter(instance=self.instance).order_by('version').last()
        if ish:
            return ish.version + 1
        return 0

    class Meta:
        model = InstanceStatusHistory

    class Params:
        status_name = "active"

