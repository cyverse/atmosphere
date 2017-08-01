from rest_framework.test import APITestCase, APIRequestFactory,\
    force_authenticate
from api.v2.views import ImageViewSet as ViewSet
from .base import APISanityTestCase
from api.tests.factories import (
    AnonymousUserFactory,
    ApplicationVersionFactory,
    ProviderFactory,
    IdentityFactory,
    ImageFactory,
    ProviderMachineFactory,
    UserFactory
)
from django.core.urlresolvers import reverse

EXPECTED_FIELD_COUNT = 13


class ApplicationTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:application'

    def setUp(self):
        factory = APIRequestFactory()
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.provider = ProviderFactory.create()
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user,
            provider=self.provider)
        self.private_image = ImageFactory.create(
            created_by=self.user,
            private=True)
        self.private_version = ApplicationVersionFactory.create_version(
            self.user, self.user_identity,
            application=self.private_image
        )
        self.private_machine = ProviderMachineFactory.create_provider_machine(
            self.user, self.user_identity,
            application=self.private_image,
            version=self.private_version)

        self.staff_user = UserFactory.create(is_staff=True)
        self.staff_user_identity = IdentityFactory.create_identity(
            created_by=self.staff_user,
            provider=self.provider)
        self.public_image = ImageFactory.create(
            created_by=self.staff_user,
            private=False)
        self.public_version = ApplicationVersionFactory.create_version(
            self.staff_user, self.staff_user_identity,
            application=self.public_image
        )
        self.public_machine = ProviderMachineFactory.create_provider_machine(
            self.staff_user, self.staff_user_identity,
            application=self.public_image,
            version=self.public_version)

        self.list_view = ViewSet.as_view({'get': 'list'})
        list_url = reverse(self.url_route+'-list')
        self.list_request = factory.get(list_url)

        self.detail_view = ViewSet.as_view({'get': 'retrieve'})
        detail_url = reverse(self.url_route+'-detail', args=(self.user.id,))
        self.detail_request = factory.get(detail_url)

        # force_authenticate(self.list_request, user=self.user)
        # force_authenticate(self.detail_request, user=self.user)

    def test_list_is_public(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)

    def test_list_is_visible_to_authenticated_user(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)

    def test_list_response_contains_expected_fields(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        self.assertTrue(response.data.get('results'), "Expected paginated results in list_view: %s" % response.data)
        data = response.data.get('results')[0]

        self.assertEquals(
            len(data), EXPECTED_FIELD_COUNT,
            "The number of arguments has changed for GET /application (%s!=%s)"
            % (len(data), EXPECTED_FIELD_COUNT))
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('uuid', data)
        self.assertIn('name', data)
        self.assertIn('metrics_url', data)
        self.assertIn('created_by', data)
        self.assertIn('description', data)
        self.assertIn('end_date', data)
        self.assertIn('is_public', data)
        self.assertIn('icon', data)
        self.assertIn('start_date', data)
        self.assertIn('tags', data)
        self.assertIn('versions', data)

    def test_details_response_contains_expected_fields(self):
        force_authenticate(self.detail_request, user=self.user)
        response = self.detail_view(self.detail_request, pk=self.private_image.id)
        data = response.data

        self.assertEquals(
            len(data), EXPECTED_FIELD_COUNT,
            "The number of arguments has changed for GET /application/%s (%s!=%s)"
            % (self.private_image.id, data.keys(), EXPECTED_FIELD_COUNT))
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('uuid', data)
        self.assertIn('name', data)
        self.assertIn('metrics_url', data)
        self.assertIn('created_by', data)
        self.assertIn('description', data)
        self.assertIn('end_date', data)
        self.assertIn('is_public', data)
        self.assertIn('icon', data)
        self.assertIn('start_date', data)
        self.assertIn('tags', data)
        self.assertIn('versions', data)

    def test_details_is_visible_to_anonymous_user(self):
        force_authenticate(self.detail_request, user=self.anonymous_user)
        response = self.detail_view(self.detail_request, pk=self.public_image.id)
        self.assertEquals(response.status_code, 404)

    def test_details_is_visible_to_authenticated_user(self):
        force_authenticate(self.detail_request, user=self.user)
        response = self.detail_view(self.detail_request, pk=self.public_image.id)
        self.assertEquals(response.status_code, 200)
        response = self.detail_view(self.detail_request, pk=self.private_image.id)
        self.assertEquals(response.status_code, 200)

    def test_create_endpoint_does_not_exist(self):
        self.assertTrue('post' not in ViewSet.http_method_names)

    def test_update_endpoint_does_exist(self):
        self.assertTrue('put' in ViewSet.http_method_names)

    def test_delete_endpoint_does_not_exist(self):
        self.assertTrue('delete' not in ViewSet.http_method_names)
