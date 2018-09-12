from django.test import TestCase
import mock
from requests.exceptions import ReadTimeout

from jetstream.plugins.auth.validation import XsedeProjectRequired
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

        # Simulate offline TAS api by throwing requests.exceptions.ReadTimeout
        with mock.patch('jetstream.tas_api.requests.get') as mock_requests_get:
            mock_requests_get.side_effect = ReadTimeout("Unknown network failure")
            self.assertTrue(plugin.validate_user(self.user))

    def test_offline_validation_when_user_has_no_allocations(self):
        """
        Offline user validation should return that a user is invalid if they
        have no existing allocations in the database
        """
        plugin = XsedeProjectRequired()

        # Simulate offline TAS api by throwing requests.exceptions.ReadTimeout
        with mock.patch('jetstream.tas_api.requests.get') as mock_requests_get:
            mock_requests_get.side_effect = ReadTimeout("Unknown network failure")
            self.assertFalse(plugin.validate_user(self.user))
