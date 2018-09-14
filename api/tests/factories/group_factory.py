import factory
from factory import fuzzy
from core.models import Group


class GroupFactory(factory.DjangoModelFactory):
    class Meta:
        model = Group

    name = fuzzy.FuzzyText(prefix="name-")
