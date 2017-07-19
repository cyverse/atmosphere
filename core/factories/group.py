import factory
from factory.django import DjangoModelFactory

from core.models import group as models


class GroupFactory(DjangoModelFactory):

    class Meta:
        model = models.Group
    name = "New Test Group"

class GroupMembershipFactory(DjangoModelFactory):

    class Meta:
        model = models.GroupMembership
