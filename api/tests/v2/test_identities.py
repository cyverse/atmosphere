from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import IdentityViewSet as ViewSet
from api.tests.factories import UserFactory, AnonymousUserFactory,\
    IdentityFactory, ProviderFactory, GroupFactory,\
    IdentityMembershipFactory, QuotaFactory, AllocationFactory
from django.core.urlresolvers import reverse
from core.models import Identity

EXPECTED_FIELD_COUNT = 12

class GetListTests(APITestCase):

    def setUp(self):
        self.view = ViewSet.as_view({'get': 'list'})
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
        self.allocation = AllocationFactory.create()
        IdentityMembershipFactory.create(
            member=self.group,
            identity=self.identity
        )

        factory = APIRequestFactory()
        url = reverse('api:v2:identity-list')
        self.request = factory.get(url)
        force_authenticate(self.request, user=self.user)
        self.response = self.view(self.request)

    def test_is_not_public(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_is_visible_to_authenticated_user(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 200)

    def test_response_is_paginated(self):
        response = self.response
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        data = response.data.get('results')
        self.assertTrue(data, "Response contained no results")
        identity_data = data[0]

        self.assertEquals(len(identity_data), EXPECTED_FIELD_COUNT, "The number of arguments has changed for GET /identity (%s!=%s)" % (len(identity_data), EXPECTED_FIELD_COUNT))
        self.assertIn('id', identity_data)
        self.assertIn('uuid', identity_data)
        self.assertIn('url', identity_data)
        self.assertIn('quota', identity_data)
        self.assertIn('allocation', identity_data)
        self.assertIn('provider', identity_data)
        self.assertIn('user', identity_data)
        self.assertIn('key', identity_data)
        self.assertIn('credentials', identity_data)
        self.assertIn('is_leader', identity_data)
        self.assertIn('members', identity_data)


class GetDetailTests(APITestCase):

    def setUp(self):
        self.view = ViewSet.as_view({'get': 'retrieve'})
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
        self.allocation = AllocationFactory.create()
        IdentityMembershipFactory.create(
            member=self.group,
            identity=self.identity,
        )

        factory = APIRequestFactory()
        url = reverse('api:v2:identity-detail', args=(self.identity.id,))
        self.request = factory.get(url)
        force_authenticate(self.request, user=self.user)
        self.response = self.view(self.request, pk=self.identity.id)

    def test_is_not_public(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request, pk=self.identity.id)
        self.assertEquals(response.status_code, 403)

    def test_is_visible_to_authenticated_user(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.identity.id)
        self.assertEquals(response.status_code, 200)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.identity.id)
        data = response.data

        self.assertEquals(
            len(data), EXPECTED_FIELD_COUNT,
            "The number of arguments has changed for GET /identity/%s (%s!=%s)" % (self.identity.id, len(data), EXPECTED_FIELD_COUNT)
        )
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertIn('url', data)
        self.assertIn('quota', data)
        self.assertIn('allocation', data)
        self.assertIn('provider', data)
        self.assertIn('user', data)
        self.assertIn('key', data)
        self.assertIn('credentials', data)
        self.assertIn('is_leader', data)
        self.assertIn('members', data)


class CreateTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('post' not in ViewSet.http_method_names)


class UpdateTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('put' not in ViewSet.http_method_names)


class DeleteTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('delete' not in ViewSet.http_method_names)
