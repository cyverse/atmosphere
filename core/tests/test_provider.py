from django.test import TestCase

from core.factories import GroupWithDataFactory


class ProviderTest(TestCase):
    def setUp(self):
        self.group = GroupWithDataFactory(name='test')

    def test_sharing_an_existing_shared_provider(self):
        providers = self.group.providers.all()

        # Share a provider that is a member of this group
        providers[0].share(self.group)
        updated_providers = self.group.providers.all()

        # Check that the number of providers has not changed
        self.assertEqual(len(updated_providers), len(providers))
