from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import UserViewSet
from api.tests.factories import UserFactory, AnonymousUserFactory
from django.core.urlresolvers import reverse
from core.models import AtmosphereUser as User


class GetListTests(APITestCase):

    def setUp(self):
        self.view = UserViewSet.as_view({'get': 'list'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.staff_user = UserFactory.create(is_staff=True)

        factory = APIRequestFactory()
        url = reverse('api:v2:atmosphereuser-list')
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
        self.assertIn('uuid', data)
        self.assertIn('url', data)
        self.assertIn('username', data)
        self.assertIn('end_date', data)


class GetDetailTests(APITestCase):

    def setUp(self):
        self.view = UserViewSet.as_view({'get': 'retrieve'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()

        factory = APIRequestFactory()
        url = reverse('api:v2:atmosphereuser-detail', args=(self.user.id,))
        self.request = factory.get(url)

    def test_is_not_public(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request, pk=self.user.id)
        self.assertEquals(response.status_code, 403)

    def test_is_visible_to_authenticated_user(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.user.id)
        self.assertEquals(response.status_code, 200)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.user.id)
        data = response.data

        self.assertEquals(len(data), 5)
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertIn('url', data)
        self.assertIn('username', data)
        self.assertIn('end_date', data)


class CreateTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('post' not in UserViewSet.http_method_names)


class UpdateTests(APITestCase):

    def test_endpoint_does_exist(self):
        self.assertTrue('put' in UserViewSet.http_method_names)


class DeleteTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('delete' not in UserViewSet.http_method_names)
