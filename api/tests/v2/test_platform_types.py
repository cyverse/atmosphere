from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import PlatformTypeViewSet as ViewSet
from api.tests.factories import UserFactory, AnonymousUserFactory, GroupFactory, PlatformTypeFactory
from django.core.urlresolvers import reverse
from .base import APISanityTestCase


class PlatformTypeTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:platformtype'

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.staff_user = UserFactory.create(is_staff=True)

        self.platform_type = PlatformTypeFactory.create()

        factory = APIRequestFactory()

        self.detail_view = ViewSet.as_view({'get': 'retrieve'})
        detail_url = reverse(
            self.url_route+'-detail', args=(self.platform_type.id,))
        self.detail_request = factory.get(detail_url)

        self.list_view = ViewSet.as_view({'get': 'list'})
        list_url = reverse(
            self.url_route+'-list')
        self.list_request = factory.get(list_url)

    def test_list_is_not_public(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 403)

    def test_list_is_visible_to_authenticated_user(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)

    def test_list_response_contains_expected_fields(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        data = response.data.get('results')[0]

        self.assertEquals(len(data), 5)
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('name', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)

    def test_is_not_public(self):
        force_authenticate(self.detail_request, user=self.anonymous_user)
        response = self.detail_view(self.detail_request, pk=self.platform_type.id)
        self.assertEquals(response.status_code, 403)

    def test_is_visible_to_authenticated_user(self):
        force_authenticate(self.detail_request, user=self.user)
        response = self.detail_view(self.detail_request, pk=self.platform_type.id)
        self.assertEquals(response.status_code, 200)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.detail_request, user=self.user)
        response = self.detail_view(self.detail_request, pk=self.platform_type.id)
        data = response.data

        self.assertEquals(len(data), 5)
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('name', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)

    def test_create_endpoint_does_not_exist(self):
        self.assertTrue('post' not in ViewSet.http_method_names)

    def test_update_endpoint_does_not_exist(self):
        self.assertTrue('put' not in ViewSet.http_method_names)

    def test_delete_endpoint_does_not_exist(self):
        self.assertTrue('delete' not in ViewSet.http_method_names)
