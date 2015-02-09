from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import ProviderViewSet
from .factories import ProviderFactory, UserFactory, AnonymousUserFactory, GroupFactory, ProviderMembershipFactory
from django.core.urlresolvers import reverse
from core.models import Provider
from rest_framework.authtoken.models import Token


class GetProviderListTests(APITestCase):
    def setUp(self):
        self.providers = ProviderFactory.create_batch(10)
        self.view = ProviderViewSet.as_view({'get': 'list'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.staff_user = UserFactory.create(is_staff=True)

        group = GroupFactory.create(name=self.user.username)
        ProviderMembershipFactory.create(member=group, provider=self.providers[0])
        ProviderMembershipFactory.create(member=group, provider=self.providers[1])
        self.membership_count = 2

        factory = APIRequestFactory()
        url = reverse('api_v2:provider-list')
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

    def test_user_only_sees_providers_they_have_access_to(self):
        response = self.response
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.data['results']), self.membership_count)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        data = response.data.get('results')[0]

        self.assertEquals(len(data), 11)
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('name', data)
        self.assertIn('description', data)
        self.assertIn('public', data)
        self.assertIn('active', data)
        self.assertIn('type', data)
        self.assertIn('virtualization', data)
        self.assertIn('sizes', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)


class GetProviderDetailTests(APITestCase):
    def setUp(self):
        self.providers = ProviderFactory.create_batch(2)
        self.view = ProviderViewSet.as_view({'get': 'retrieve'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.staff_user = UserFactory.create(is_staff=True)

        group = GroupFactory.create(name=self.user.username)
        self.yes_provider = self.providers[0]
        ProviderMembershipFactory.create(member=group, provider=self.yes_provider)
        self.no_provider = self.providers[1]

        factory = APIRequestFactory()
        url = reverse('api_v2:provider-detail', args=(self.yes_provider.id,))
        self.request = factory.get(url)

    def test_is_not_public(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request, pk=self.yes_provider.id)
        self.assertEquals(response.status_code, 403)

    def test_user_can_see_provider_they_have_access_to(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.yes_provider.id)
        self.assertEquals(response.status_code, 200)

    def test_user_cannot_see_provider_they_do_not_have_access_to(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.no_provider.id)
        self.assertEquals(response.status_code, 404)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.yes_provider.id)
        data = response.data

        self.assertEquals(len(data), 11)
        self.assertIn('id', data)
        self.assertIn('url', data)
        self.assertIn('name', data)
        self.assertIn('description', data)
        self.assertIn('public', data)
        self.assertIn('active', data)
        self.assertIn('type', data)
        self.assertIn('virtualization', data)
        self.assertIn('sizes', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)


class CreateProviderTests(APITestCase):
    def test_endpoint_does_not_exist(self):
        self.assertTrue('post' not in ProviderViewSet.http_method_names)


class UpdateProviderTests(APITestCase):
    def test_endpoint_does_not_exist(self):
        self.assertTrue('put' not in ProviderViewSet.http_method_names)


class DeleteProviderTests(APITestCase):
    def test_endpoint_does_not_exist(self):
        self.assertTrue('delete' not in ProviderViewSet.http_method_names)

