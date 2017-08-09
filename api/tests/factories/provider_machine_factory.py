import factory
import uuid
from core.models import ProviderMachine, InstanceSource
from .provider_factory import ProviderFactory
from .version_factory import ApplicationVersionFactory
from .user_factory import UserFactory
from .image_factory import ImageFactory


class InstanceSourceFactory(factory.DjangoModelFactory):
    provider = factory.SubFactory(ProviderFactory)
    created_by = factory.SubFactory(UserFactory)

    class Meta:
        model = InstanceSource

    identifier = factory.Sequence(lambda n: uuid.uuid4())


class ProviderMachineFactory(factory.DjangoModelFactory):

    application_version = factory.SubFactory(ApplicationVersionFactory)
    instance_source = factory.SubFactory(InstanceSourceFactory)

    @staticmethod
    def create_provider_machine(user, identity, application=None, version=None):
        if version and not application:
            application = version.application
        if not application:
            application = ImageFactory.create(
                created_by_identity=identity,
                created_by=user)
        if not version:
            version = ApplicationVersionFactory.create(
                application=application,
                created_by_identity=identity,
                created_by=user)
        source = InstanceSourceFactory.create(
            provider=identity.provider,
            created_by_identity=identity,
            created_by=user)
        machine = ProviderMachineFactory.create(
            instance_source=source,
            application_version=version)
        return machine

    class Meta:
        model = ProviderMachine
