import factory
from core.models import ProviderMachine, InstanceSource
from .version_factory import ApplicationVersionFactory
from .image_factory import ImageFactory


class ProviderMachineFactory(factory.DjangoModelFactory):

    @staticmethod
    def create_provider_machine(user, identity):
        application = ImageFactory.create(
            created_by_identity=identity,
            created_by=user)
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


class InstanceSourceFactory(factory.DjangoModelFactory):

    class Meta:
        model = InstanceSource


