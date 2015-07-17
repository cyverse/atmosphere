import factory
from core.models import Group


class GroupFactory(factory.DjangoModelFactory):

    class Meta:
        model = Group
