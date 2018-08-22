import requests

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from django.core.urlresolvers import reverse

from api.v2.views import AccessTokenViewSet
from api.tests.factories import UserFactory, AnonymousUserFactory
from core.models.access_token import AccessToken, create_access_token

from .base import APISanityTestCase


class AccessTokenTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:access_token'

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.access_token = create_access_token(self.user, "Test Token 1", issuer="Testing")

        factory = APIRequestFactory()

        self.create_view = AccessTokenViewSet.as_view({'post': 'create'})
        self.create_request = factory.post(self.url_route, {'name': 'Test Token Creation'})
        self.invalid_create_request = factory.post(self.url_route, {'name': {'Not': 'A String'}}, format='json')

        self.list_view = AccessTokenViewSet.as_view({'get': 'list'})
        self.list_request = factory.get(self.url_route)

        self.delete_view = AccessTokenViewSet.as_view({'delete': 'destroy'})
        self.delete_request = factory.delete('{}/{}'.format(self.url_route, self.access_token.id))

        self.edit_view = AccessTokenViewSet.as_view({'put': 'update'})
        self.edit_request = factory.put('{}/{}'.format(self.url_route, self.access_token.id), {'name': 'Test Token New Name'})
        self.invalid_edit_request = factory.put('{}/{}'.format(self.url_route, self.access_token.id), {'name': {'Not': 'A String'}}, format='json')

    def test_list(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)

    def test_list_not_public(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 403)

    def test_list_multiple_tokens(self):
        create_access_token(self.user, "Test Token 2", issuer="Testing")
        create_access_token(self.user, "Test Token 3", issuer="Testing")
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.data.get('results')), 3)

    def test_list_response_contains_expected_fields(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        data = response.data.get('results')[0]
        self.assertEquals(len(data), 3)
        self.assertIn('name', data)
        self.assertIn('id', data)
        self.assertIn('issued_time', data)

    def test_create_response_contains_expected_fields(self):
        force_authenticate(self.create_request, user=self.user)
        response = self.create_view(self.create_request)
        data = response.data
        self.assertEquals(len(data), 4)
        self.assertIn('id', data)
        self.assertIn('token', data)
        self.assertIn('issued_time', data)
        self.assertIn('name', data)

    def test_create_not_public(self):
        force_authenticate(self.create_request, user=self.anonymous_user)
        response = self.create_view(self.create_request)
        self.assertEquals(response.status_code, 403)

    def test_edit(self):
        force_authenticate(self.edit_request, user=self.user)
        edit_response = self.edit_view(self.edit_request, pk=self.access_token.id)
        # Get edited token using list_request and finding token by id
        force_authenticate(self.list_request, user=self.user)
        list_response = self.list_view(self.list_request)
        data = list_response.data.get('results')
        token = [x for x in data if x.get('id') == self.access_token.id]
        self.assertEquals(len(token), 1)
        token = token[0]
        # Now test token
        self.assertEquals(token.get('id'), self.access_token.id)
        self.assertEquals(token.get('name'), 'Test Token New Name')
        self.assertEquals(edit_response.data.get('name'), 'Test Token New Name')

    def test_edit_not_public(self):
        force_authenticate(self.edit_request, user=self.anonymous_user)
        response = self.edit_view(self.edit_request, pk=self.access_token.id)
        self.assertEquals(response.status_code, 403)

    def test_delete(self):
        force_authenticate(self.delete_request, user=self.user)
        delete_response = self.delete_view(self.delete_request, pk=self.access_token.id)
        force_authenticate(self.list_request, user=self.user)
        list_response = self.list_view(self.list_request)
        data = list_response.data.get('results')
        self.assertEquals(len(data), 0)

    def test_delete_not_public(self):
        force_authenticate(self.delete_request, user=self.anonymous_user)
        response = self.delete_view(self.delete_request, pk=self.access_token.id)
        self.assertEquals(response.status_code, 403)

    def test_invalid_create(self):
        force_authenticate(self.invalid_create_request, user=self.user)
        response = self.create_view(self.invalid_create_request)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data['name'], ["Not a valid string."])

    def test_invalid_edit(self):
        force_authenticate(self.invalid_edit_request, user=self.user)
        response = self.edit_view(self.invalid_edit_request, pk=self.access_token.id)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data['name'], ["Not a valid string."])
