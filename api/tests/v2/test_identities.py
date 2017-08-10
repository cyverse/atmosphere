from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import IdentityViewSet as ViewSet
from .base import APISanityTestCase
from api.tests.factories import UserFactory, AnonymousUserFactory,\
    IdentityFactory, ProviderFactory, GroupFactory,\
    IdentityMembershipFactory, QuotaFactory
from django.core.urlresolvers import reverse


EXPECTED_FIELD_COUNT = 11


class IdentityTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:identity'

    def setUp(self):
        self.list_view = ViewSet.as_view({'get': 'list'})
        self.detailed_view = ViewSet.as_view({'get': 'retrieve'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.staff_user = UserFactory.create(is_staff=True)

        self.provider = ProviderFactory.create()
        self.quota = QuotaFactory.create()
        self.identity = IdentityFactory.create(
            provider=self.provider,
            quota=self.quota,
            created_by=self.user)
        IdentityMembershipFactory.create(
            member=self.group,
            identity=self.identity,
        )

        factory = APIRequestFactory()
        detail_url = reverse('api:v2:identity-detail', args=(self.identity.id,))
        self.detail_request = factory.get(detail_url)

        list_url = reverse('api:v2:identity-list')
        self.list_request = factory.get(list_url)

    def test_is_not_public(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 403)

    def test_is_visible_to_authenticated_user(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)

    def test_list_response_contains_expected_fields(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        data = response.data.get('results')
        self.assertTrue(data, "Response contained no results")
        identity_data = data[0]

        self.assertEquals(
            len(identity_data), EXPECTED_FIELD_COUNT,
            "The number of arguments has changed for GET /identity (%s!=%s)"
            % (len(identity_data), EXPECTED_FIELD_COUNT))
        self.assertIn('id', identity_data)
        self.assertIn('uuid', identity_data)
        self.assertIn('url', identity_data)
        self.assertIn('quota', identity_data)
        self.assertIn('provider', identity_data)
        self.assertIn('user', identity_data)
        self.assertIn('key', identity_data)
        self.assertIn('credentials', identity_data)
        self.assertIn('is_leader', identity_data)
        self.assertIn('members', identity_data)

    def test_detail_is_not_public(self):
        force_authenticate(self.detail_request, user=self.anonymous_user)
        response = self.detailed_view(self.detail_request, pk=self.identity.id)
        self.assertEquals(response.status_code, 403)

    def test_detail_is_visible_to_authenticated_user(self):
        force_authenticate(self.detail_request, user=self.user)
        response = self.detailed_view(self.detail_request, pk=self.identity.id)
        self.assertEquals(response.status_code, 200)

    def test_detail_response_contains_expected_fields(self):
        force_authenticate(self.detail_request, user=self.user)
        response = self.detailed_view(self.detail_request, pk=self.identity.id)
        data = response.data

        self.assertEquals(
            len(data), EXPECTED_FIELD_COUNT,
            "The number of arguments has changed for GET /identity/%s (%s!=%s)"
            % (self.identity.id, len(data), EXPECTED_FIELD_COUNT)
        )
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertIn('url', data)
        self.assertIn('quota', data)
        self.assertIn('provider', data)
        self.assertIn('user', data)
        self.assertIn('key', data)
        self.assertIn('credentials', data)
        self.assertIn('is_leader', data)
        self.assertIn('members', data)

    def test_create_does_not_exist(self):
        self.assertTrue('post' not in ViewSet.http_method_names)

    def test_update_does_not_exist(self):
        self.assertTrue('put' not in ViewSet.http_method_names)

    def test_delete_does_not_exist(self):
        self.assertTrue('delete' not in ViewSet.http_method_names)
