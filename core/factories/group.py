import factory
from factory.django import DjangoModelFactory

from core.models import group as models


class GroupFactory(DjangoModelFactory):

    class Meta:
        model = models.Group

    name = "New Test Group"


class LeadershipFactory(DjangoModelFactory):

    class Meta:
        model = models.Leadership

    user = factory.SubFactory("core.factories.user.AtmosphereUserFactory",
                              selected_identity=None)
    group = factory.SubFactory(GroupFactory)


#    class Meta:
#
#
#
#    class Meta:
#
#
#
#    class Meta:
#
#
#
#    class Meta:
#


class GroupWithDataFactory(GroupFactory):
    leaders = factory.RelatedFactory(LeadershipFactory, "group")
#        ApplicationMembershipFactory, "group")
#        ProviderMachineMembershipFactory, "group")
