import factory
from core.models import Identity
from .user_factory import UserFactory
from .group_factory import GroupFactory
from .quota_factory import QuotaFactory
from .provider_factory import ProviderFactory
from .leadership_factory import LeadershipFactory
from .identity_membership_factory import IdentityMembershipFactory


class IdentityFactory(factory.DjangoModelFactory):

    @staticmethod
    def create_identity(created_by, group=None, provider=None, quota=None):
        if not created_by:
            created_by = UserFactory.create()
        if not group:
            group = GroupFactory.create(name=created_by.username)
        LeadershipFactory(user=created_by, group=group)
        if not provider:
            provider = ProviderFactory.create()
        if not quota:
            quota = QuotaFactory.create()
        identity = IdentityFactory.create(
            provider=provider,
            quota=quota,
            created_by=created_by)
        IdentityMembershipFactory.create(
            member=group,
            identity=identity
        )
        return identity

    class Meta:
        model = Identity
