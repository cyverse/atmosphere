import factory
from core.models import ProjectInstance
from .project_factory import ProjectFactory
from .instance_factory import InstanceFactory


class ProjectInstanceFactory(factory.DjangoModelFactory):

    class Meta:
        model = ProjectInstance

    project = factory.SubFactory(ProjectFactory)
    instance = factory.SubFactory(InstanceFactory)
