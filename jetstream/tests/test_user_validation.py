from django.test import TestCase, override_settings
import mock

from jetstream.plugins.auth.validation import XsedeProjectRequired
from jetstream.exceptions import TASAPIException
from api.tests.factories import UserFactory, UserAllocationSourceFactory

# Create an instance
# build identical instance status history timings and try to add them
# It should fail and force you to do 'the right thing only'


class TestOfflineUserValidation(TestCase):
    def setUp(self):
        self.user = UserFactory.create()

    def test_offline_validation_when_user_has_allocations(self):
        """
        Offline user validation should return that a user is valid if they
        have existing allocations in the database.
        """

        plugin = XsedeProjectRequired()

        # Create an allocation for the user
        UserAllocationSourceFactory.create(user=self.user)

        # Simulate offline TAS api by throwing TASAPIException
        with mock.patch('jetstream.allocation.tacc_api_get') as mock_tacc_api_get:
            mock_tacc_api_get.side_effect = TASAPIException("Unknown network failure")
            self.assertTrue(plugin.validate_user(self.user))

    def test_offline_validation_when_user_has_no_allocations(self):
        """
        Offline user validation should return that a user is invalid if they
        have no existing allocations in the database
        """
        plugin = XsedeProjectRequired()

        # Simulate offline TAS api by throwing TASAPIException
        with mock.patch('jetstream.allocation.tacc_api_get') as mock_tacc_api_get:
            mock_tacc_api_get.side_effect = TASAPIException("Unknown network failure")
            self.assertFalse(plugin.validate_user(self.user))
