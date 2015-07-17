import factory
from core.models import Project


class ProjectFactory(factory.DjangoModelFactory):

    class Meta:
        model = Project

    name = 'project name'
    description = 'project description'
