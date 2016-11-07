from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import IdentityViewSet as ViewSet
from api.tests.factories import UserFactory, AnonymousUserFactory,\
    IdentityFactory, ProviderFactory, GroupFactory,\
    IdentityMembershipFactory, QuotaFactory, AllocationFactory,\
    LeadershipFactory
from django.core.urlresolvers import reverse
from core.models import Identity


class GetListTests(APITestCase):

    def setUp(self):
        self.view = ViewSet.as_view({'get': 'list'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.leadership = LeadershipFactory.create(
            user=self.user,
            group=self.group
            )
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
        data = response.data.get('results')[0]

        self.assertEquals(len(data), 8, "The number of arguments has changed for GET /identity")
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertIn('url', data)
        self.assertIn('quota', data)
        self.assertIn('allocation', data)
        self.assertIn('provider', data)
        self.assertIn('user', data)


class GetDetailTests(APITestCase):

    def setUp(self):
        self.view = ViewSet.as_view({'get': 'retrieve'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.leadership = LeadershipFactory.create(
            user=self.user,
            group=self.group
            )
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
            quota=self.quota
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

        self.assertEquals(len(data), 8, "The number of arguments has changed for GET /identity/:identityID")
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertIn('url', data)
        self.assertIn('quota', data)
        self.assertIn('allocation', data)
        self.assertIn('provider', data)
        self.assertIn('user', data)


class CreateTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('post' not in ViewSet.http_method_names)


class UpdateTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('put' not in ViewSet.http_method_names)


class DeleteTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('delete' not in ViewSet.http_method_names)
