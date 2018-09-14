import factory
from core.models import Instance
from django.utils import timezone
from .user_factory import UserFactory
from .project_factory import ProjectFactory
from .provider_machine_factory import ProviderMachineFactory
from .identity_factory import IdentityFactory


class InstanceFactory(factory.DjangoModelFactory):
    class Meta:
        model = Instance
        exclude = ('provider_machine', )

    provider_machine = factory.SubFactory(ProviderMachineFactory)
    start_date = factory.LazyFunction(timezone.now)
    project = factory.SubFactory(ProjectFactory)
    source = factory.SelfAttribute('provider_machine.instance_source')
    created_by = factory.SubFactory(UserFactory)
    created_by_identity = factory.LazyAttribute(
        lambda model: IdentityFactory(created_by=model.created_by)
    )
