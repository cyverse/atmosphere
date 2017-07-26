import factory
from core.models import Identity
from .user_factory import UserFactory
from .group_factory import GroupFactory
from .group_membership_factory import GroupMembershipFactory
from .quota_factory import QuotaFactory
from .provider_factory import ProviderFactory
from .identity_membership_factory import IdentityMembershipFactory


class IdentityFactory(factory.DjangoModelFactory):

    @staticmethod
    def create_identity(created_by, group=None, provider=None, quota=None):
        if not created_by:
            created_by = UserFactory.create()
        if not group:
            group = GroupFactory.create(name=created_by.username)
        group.user_set.add(created_by)
        GroupMembershipFactory.create(
            user=created_by,
            group=group,
            is_leader=True)
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
