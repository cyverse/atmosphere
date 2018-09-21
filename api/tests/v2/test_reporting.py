from unittest import skip

from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from api.tests.factories import UserFactory, AnonymousUserFactory
from api.v2.views import ReportingViewSet
from core.models import AtmosphereUser


def contains_user(username):
    """
    Test if the username exists
    """
    try:
        AtmosphereUser.objects.get_by_natural_key(username=username)
        return True
    except AtmosphereUser.DoesNotExist:
        return False


class ReportingTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.view = ReportingViewSet.as_view({'get': 'list'})

    def test_is_not_public(self):
        factory = APIRequestFactory()
        url = reverse('api:v2:reporting-list')
        request = factory.get(url)
        force_authenticate(request, user=self.anonymous_user)
        response = self.view(request)
        self.assertEquals(response.status_code, 403)

    def test_no_query_params(self):
        factory = APIRequestFactory()
        url = reverse('api:v2:reporting-list')
        request = factory.get(url)
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEquals(response.status_code, 400)
        self.assertEqual(
            response.data['errors'][0]['message'],
            "The reporting API should be accessed via the query parameters:"
            " ['start_date', 'end_date', 'provider_id']"
        )

    def test_invalid_query_params(self):
        factory = APIRequestFactory()
        invalid_urls = [
            'api/v2/reporting?start_date=3077-10-29&end_date=1901-10-29&provider_id=some_provider',
            'api/v2/reporting?start_date=blah&end_date=1901-10-29&provider_id=1',
            'api/v2/reporting?start_date=3077-10-29&end_date=blah&provider_id=1'
        ]
        for url in invalid_urls:
            request = factory.get(url)
            force_authenticate(request, user=self.user)
            response = self.view(request)
            self.assertEquals(response.status_code, 400)
            self.assertEqual(
                response.data['errors'][0]['message'],
                'Invalid filter parameters'
            )

    @skip('skip for now')
    def test_access_invalid_provider(self):
        raise NotImplementedError

    @skip('skip for now')
    def test_access_not_allowed_provider(self):
        raise NotImplementedError
