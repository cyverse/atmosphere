import factory
from factory import fuzzy
from core.models import Project

from .group_factory import GroupFactory
from .user_factory import UserFactory


class ProjectFactory(factory.DjangoModelFactory):

    class Meta:
        model = Project

    name = fuzzy.FuzzyText(prefix="name-")
    description = fuzzy.FuzzyText(prefix="description-")
    created_by = factory.SubFactory(UserFactory)
    owner = factory.SubFactory(GroupFactory)
