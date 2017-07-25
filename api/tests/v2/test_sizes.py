from rest_framework.test import APITestCase, APIRequestFactory,\
    force_authenticate

from django.core.urlresolvers import reverse
from core.models import Size
from api.v2.views import SizeViewSet
from api.tests.factories import ProviderFactory, UserFactory,\
    AnonymousUserFactory, SizeFactory, IdentityFactory

from .base import APISanityTestCase


class SizeTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:size'

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.provider = ProviderFactory.create()
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user,
            provider=self.provider)
        self.size = SizeFactory.create(provider=self.provider,
                                       cpu=10,
                                       disk=20,
                                       root=0,
                                       mem=126)
        self.list_view = SizeViewSet.as_view({'get': 'list'})
        factory = APIRequestFactory()

        list_url = reverse(self.url_route+'-list')
        self.list_request = factory.get(list_url)

    def test_is_public(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)

    def test_response_is_paginated(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.data['count'], 1)
        self.assertEquals(len(response.data.get('results')), 1)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        data = response.data.get('results')[0]
        self.assertTrue(data, "No results retrieved.")
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data), 13, "Number of fields does not match")
        self.assertEquals(data['id'], self.size.id)
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.size.name)
        self.assertEquals(data['alias'], self.size.alias)
        self.assertIn('uuid', data)
        self.assertIn('cpu', data)
        self.assertIn('disk', data)
        self.assertIn('root', data)
        self.assertIn('mem', data)
        self.assertIn('active', data)
        self.assertIn('provider', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)
