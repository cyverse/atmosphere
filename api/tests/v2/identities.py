from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import IdentityViewSet as ViewSet
from .factories import UserFactory, AnonymousUserFactory, IdentityFactory, ProviderFactory, GroupFactory, \
    ProviderMembershipFactory, IdentityMembershipFactory, QuotaFactory, AllocationFactory
from django.core.urlresolvers import reverse
from core.models import Identity


class GetListTests(APITestCase):
    def setUp(self):
        self.view = ViewSet.as_view({'get': 'list'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.staff_user = UserFactory.create(is_staff=True)

        self.provider = ProviderFactory.create()
        self.identity = IdentityFactory.create(provider=self.provider, created_by=self.user)
        self.quota = QuotaFactory.create()
        self.allocation = AllocationFactory.create()
        IdentityMembershipFactory.create(
            member=self.group,
            identity=self.identity,
            quota=self.quota
        )
        ProviderMembershipFactory.create(member=self.group, provider=self.provider)

        factory = APIRequestFactory()
        url = reverse('api_v2:identity-list')
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

        self.assertEquals(len(data), 5)
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('quota', data)
        self.assertIn('allocation', data)
        self.assertIn('user', data)


class GetDetailTests(APITestCase):
    def setUp(self):
        self.view = ViewSet.as_view({'get': 'retrieve'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.staff_user = UserFactory.create(is_staff=True)

        self.provider = ProviderFactory.create()
        self.identity = IdentityFactory.create(provider=self.provider, created_by=self.user)
        self.quota = QuotaFactory.create()
        self.allocation = AllocationFactory.create()
        IdentityMembershipFactory.create(
            member=self.group,
            identity=self.identity,
            quota=self.quota
        )
        ProviderMembershipFactory.create(member=self.group, provider=self.provider)

        factory = APIRequestFactory()
        url = reverse('api_v2:identity-detail', args=(self.identity.id,))
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

        self.assertEquals(len(data), 5)
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('quota', data)
        self.assertIn('allocation', data)
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

