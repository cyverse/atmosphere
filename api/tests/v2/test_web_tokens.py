from django.core.urlresolvers import reverse
from django.urls import resolve
from django.test import override_settings
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
import urllib
import random

from api.v2.views import WebTokenView
from api.tests.factories import UserFactory

class WebTokenTests(APITestCase):
    def test_url_resolution(self):
        """
        Url config correctly resolves uuids
        """
        match = resolve('/api/v2/web_tokens/d71e6b24-841e-4b77-a819-01098579e6a9')

        # Assert that a match exists (that the result is truthy)
        self.assertTrue(match)

    def test_api_response_missing_client_param(self):
        """
        An error is returned when a query is made without specifiying a client
        """
        response = create_get_request(query_params={})
        self.assertEqual(response.status_code, 400)

        messages = [ err["message"] for err in response.data['errors'] ]
        self.assertIn(
            'Invalid or missing "client" query paramater', messages)

    def test_api_with_request_for_web_desktop(self):
        """
        A token is returned for an active instance for web_desktop
        """
        response = create_get_request(query_params={'client': 'web_desktop'})
        self.assertEqual(response.status_code, 200)

        for key in ['token', 'token_url']:
            self.assertIn(key, response.data)

    @override_settings(GUACAMOLE_ENABLED=False)
    def test_api_with_request_for_guacamole_when_not_enabled(self):
        """
        A web token for guacamole requires GUACAMOLE_ENABLED
        """
        response = create_get_request(query_params={'client': 'guacamole'})
        self.assertEqual(response.status_code, 400)



def create_an_instance(user=None, ip_address=None):
    # This method should be replaced when the InstanceFactory can create an
    # instance w/o requiring any arguments
    import uuid
    from api.tests.factories import (
        UserFactory, InstanceFactory, ProviderMachineFactory, IdentityFactory,
        ProviderFactory)
    from django.utils import timezone

    if not user:
        user = UserFactory.create()
    staff_user = UserFactory.create(is_staff=True, is_superuser=True)
    provider = ProviderFactory.create()
    user_identity = IdentityFactory.create_identity(
        created_by=user,
        provider=provider)
    staff_user_identity = IdentityFactory.create_identity(
        created_by=staff_user,
        provider=provider)
    machine = ProviderMachineFactory.create_provider_machine(staff_user, staff_user_identity)
    start_date = timezone.now()
    return InstanceFactory.create(
        name="",
        provider_alias=uuid.uuid4(),
        source=machine.instance_source,
        ip_address=ip_address,
        created_by=user,
        created_by_identity=user_identity,
        start_date=start_date)

def create_get_request(user=None, instance=None, query_params=None):
    if not query_params:
        query_params = {}
    if not user:
        user = UserFactory.create()
    if not instance:
        ip_address="{}.{}.{}.{}".format(
                random.randint(1,255),
                random.randint(1,255),
                random.randint(1,255),
                random.randint(1,255))
        instance = create_an_instance(user=user, ip_address=ip_address)
    view = WebTokenView.as_view()

    # Construct url
    base_url = reverse('api:v2:web_token', args=(instance.provider_alias,))
    encoded_params = urllib.urlencode(query_params)
    url = "{}?{}".format(base_url, encoded_params)

    request = APIRequestFactory().get(url)
    force_authenticate(request, user=user)
    return view(request, pk=instance.provider_alias)
