from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import AllocationViewSet as ViewSet
from api.tests.factories import UserFactory, AnonymousUserFactory, GroupFactory, AllocationFactory
from django.core.urlresolvers import reverse

# Test cases should be re-written now that these methods are allowed.
#
#class GetListTests(APITestCase):
#
#    def setUp(self):
#        self.view = ViewSet.as_view({'get': 'list'})
#        self.anonymous_user = AnonymousUserFactory()
#        self.user = UserFactory.create()
#        self.group = GroupFactory.create(name=self.user.username)
#        self.staff_user = UserFactory.create(is_staff=True)
#
#        self.allocation = AllocationFactory.create()
#
#        factory = APIRequestFactory()
#        url = reverse('api:v2:quota-list')
#        self.request = factory.get(url)
#        force_authenticate(self.request, user=self.user)
#        self.response = self.view(self.request)
#
#    def test_is_not_public(self):
#        force_authenticate(self.request, user=self.anonymous_user)
#        response = self.view(self.request)
#        self.assertEquals(response.status_code, 403)
#
#    def test_is_visible_to_authenticated_user(self):
#        force_authenticate(self.request, user=self.user)
#        response = self.view(self.request)
#        self.assertEquals(response.status_code, 200)
#
#    def test_response_is_paginated(self):
#        response = self.response
#        self.assertIn('count', response.data)
#        self.assertIn('results', response.data)
#
#    def test_response_contains_expected_fields(self):
#        force_authenticate(self.request, user=self.user)
#        response = self.view(self.request)
#        data = response.data.get('results')[0]
#
#        self.assertEquals(len(data), 4)
#        self.assertIn('id', data)
#        self.assertIn('url', data)
#        self.assertIn('threshold', data)
#        self.assertIn('delta', data)
#
#
#class GetDetailTests(APITestCase):
#
#    def setUp(self):
#        self.view = ViewSet.as_view({'get': 'retrieve'})
#        self.anonymous_user = AnonymousUserFactory()
#        self.user = UserFactory.create()
#        self.group = GroupFactory.create(name=self.user.username)
#        self.staff_user = UserFactory.create(is_staff=True)
#
#        self.allocation = AllocationFactory.create()
#
#        factory = APIRequestFactory()
#        url = reverse('api:v2:quota-detail', args=(self.allocation.id,))
#        self.request = factory.get(url)
#        force_authenticate(self.request, user=self.user)
#        self.response = self.view(self.request, pk=self.allocation.id)
#
#    def test_is_not_public(self):
#        force_authenticate(self.request, user=self.anonymous_user)
#        response = self.view(self.request, pk=self.allocation.id)
#        self.assertEquals(response.status_code, 403)
#
#    def test_is_visible_to_authenticated_user(self):
#        force_authenticate(self.request, user=self.user)
#        response = self.view(self.request, pk=self.allocation.id)
#        self.assertEquals(response.status_code, 200)
#
#    def test_response_contains_expected_fields(self):
#        force_authenticate(self.request, user=self.user)
#        response = self.view(self.request, pk=self.allocation.id)
#        data = response.data
#
#        self.assertEquals(len(data), 4)
#        self.assertIn('id', data)
#        self.assertIn('url', data)
#        self.assertIn('threshold', data)
#        self.assertIn('delta', data)
#
#
#class CreateTests(APITestCase):
#
#    def test_endpoint_does_not_exist(self):
#        self.assertTrue('post' not in ViewSet.http_method_names)
#
#
#class UpdateTests(APITestCase):
#
#    def test_endpoint_does_not_exist(self):
#        self.assertTrue('put' not in ViewSet.http_method_names)
#
#
#class DeleteTests(APITestCase):
#
#    def test_endpoint_does_not_exist(self):
#        self.assertTrue('delete' not in ViewSet.http_method_names)
