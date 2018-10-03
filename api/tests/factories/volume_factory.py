import factory
from core.models import Volume
from api.tests.factories import ProjectFactory, InstanceSourceFactory


class VolumeFactory(factory.DjangoModelFactory):
    class Meta:
        model = Volume

    project = factory.SubFactory(ProjectFactory)
    instance_source = factory.SubFactory(InstanceSourceFactory)
