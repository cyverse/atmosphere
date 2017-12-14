import factory
import uuid

from core.models import Instance
from django.utils import timezone
from .provider_machine_factory import ProviderMachineFactory
from .identity_factory import IdentityFactory
from .user_factory import UserFactory


class InstanceFactory(factory.DjangoModelFactory):

    start_date = timezone.now()
    provider_alias = uuid.uuid4()
    created_by_identity = factory.SubFactory(IdentityFactory)
    created_by = factory.SubFactory(UserFactory)

    class Meta:
        model = Instance
