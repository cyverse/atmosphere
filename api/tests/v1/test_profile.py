from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate
import mock

from api.v1.views import Profile
from api.tests.factories import UserFactory
from core.models import AtmosphereUser

class ProfileTests(TestCase):
    @override_settings(AUTO_CREATE_NEW_ACCOUNTS=True)
    def test_external_accounts_are_created(self):
        """
        Sanity check that configuration results in call to create_new_accounts.
        """
        user = UserFactory()
        url = reverse('api:v1:profile')
        view = Profile.as_view()
        factory = APIRequestFactory()
        request = factory.get(url)
        force_authenticate(request, user=user)

        with mock.patch("api.v1.views.profile.create_new_accounts") as mock_create_new_accounts:
            view(request)
            mock_create_new_accounts.assert_called_once()

    @override_settings(AUTO_CREATE_NEW_ACCOUNTS=True)
    def test_external_accounts_are_not_created_for_invalid_user(self):
        """
        Accounts are NOT created when when the user is invalid
        """
        user = UserFactory()
        url = reverse('api:v1:profile')
        view = Profile.as_view()
        factory = APIRequestFactory()
        request = factory.get(url)
        force_authenticate(request, user=user)

        # Patch the user so that they are invalid
        with mock.patch.object(AtmosphereUser, 'is_valid', return_value=False), \
                mock.patch("api.v1.views.profile.create_new_accounts") \
                as mock_create_new_accounts:
            response = view(request)
            mock_create_new_accounts.assert_not_called()
