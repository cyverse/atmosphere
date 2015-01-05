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


class ProviderMembershipFactory(DjangoModelFactory):
    class Meta:
        model = models.ProviderMembership

    provider = factory.SubFactory("core.factories.provider.ProviderFactory")
    member = factory.SubFactory(GroupFactory)


#class IdentityMembershipFactory(DjangoModelFactory):
#    class Meta:
#        model = models.IdentityMembership
#
#    identity = factory.SubFactory(IdentityFactory)
#    member = factory.SubFactory(GroupFactory)
#    quota = factory.SubFactory(QuotaFactory)
#    allocation = factory.SubFactory(AllocationFactory)
#
#
#class InstanceMembershipFactory(DjangoModelFactory):
#    class Meta:
#        model = models.InstanceMembership
#
#    instance = factory.SubFactory(InstanceFactory)
#    owner = factory.SubFactory(GroupFactory)
#
#
#class ApplicationMembershipFactory(DjangoModelFactory):
#    class Meta:
#        model = models.ApplicationMembership
#
#    application = factory.SubFactory(ApplicationFactory)
#    group = factory.SubFactory(GroupFactory)
#    can_edit = False
#
#
#class ProviderMachineMembershipFactory(DjangoModelFactory):
#    class Meta:
#        model = models.ProviderMachineMembership
#
#    provider_machine = factory.SubFactory(ProviderMachineFactory)
#    group = factory.SubFactory(GroupFactory)
#    can_share = False


class GroupWithDataFactory(GroupFactory):
    leaders = factory.RelatedFactory(LeadershipFactory, "group")
    providers = factory.RelatedFactory(ProviderMembershipFactory, "member")
#    identities = factory.RelatedFactory(IdentityMembershipFactory, "member")
#    instances = factory.RelatedFactory(InstanceMembershipFactory, "owner")
#    applications = factory.RelatedFactory(
#        ApplicationMembershipFactory, "group")
#    provider_machines = factory.RelatedFactory(
#        ProviderMachineMembershipFactory, "group")
