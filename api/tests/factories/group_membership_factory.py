import factory
from core.models import GroupMembership


class GroupMembershipFactory(factory.DjangoModelFactory):

    class Meta:
        model = GroupMembership
