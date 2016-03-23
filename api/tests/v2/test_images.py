from rest_framework.test import APITestCase, APIRequestFactory,\
    force_authenticate
from api.v2.views import ImageViewSet as ViewSet
from api.tests.factories import UserFactory, AnonymousUserFactory, ImageFactory
from django.core.urlresolvers import reverse

from unittest import skip

# class GetListTests(APITestCase):
# 
#     def setUp(self):
#         self.view = ViewSet.as_view({'get': 'list'})
#         self.anonymous_user = AnonymousUserFactory()
#         self.user = UserFactory.create()
#         self.staff_user = UserFactory.create(is_staff=True)
# 
#         self.image = ImageFactory.create(created_by=self.user)
# 
#         factory = APIRequestFactory()
#         url = reverse('api:v2:application-list')
#         self.request = factory.get(url)
#         force_authenticate(self.request, user=self.user)
#         self.response = self.view(self.request)
# 
#     def test_is_public(self):
#         force_authenticate(self.request, user=self.anonymous_user)
#         response = self.view(self.request)
#         self.assertEquals(response.status_code, 200)
# 
#     def test_is_visible_to_authenticated_user(self):
#         force_authenticate(self.request, user=self.user)
#         response = self.view(self.request)
#         self.assertEquals(response.status_code, 200)
# 
#     def test_response_is_paginated(self):
#         response = self.response
#         self.assertIn('count', response.data)
#         self.assertIn('results', response.data)
# 
#     def test_response_contains_expected_fields(self):
#         force_authenticate(self.request, user=self.user)
#         response = self.view(self.request)
#         data = response.data.get('results')[0]
# 
#         self.assertEquals(len(data), 12, "Unexepcted # of arguments in API endpoint")
#         self.assertIn('id', data)
#         self.assertIn('url', data)
#         self.assertIn('uuid', data)
#         self.assertIn('name', data)
#         self.assertIn('description', data)
#         self.assertIn('is_public', data)
#         self.assertIn('icon', data)
#         self.assertIn('tags', data)
#         self.assertIn('created_by', data)
#         self.assertIn('start_date', data)
#         self.assertIn('end_date', data)
# 
# 
# class GetDetailTests(APITestCase):
# 
#     def setUp(self):
#         self.view = ViewSet.as_view({'get': 'retrieve'})
#         self.anonymous_user = AnonymousUserFactory()
#         self.user = UserFactory.create()
# 
#         self.image = ImageFactory.create(created_by=self.user)
# 
#         factory = APIRequestFactory()
#         url = reverse('api:v2:application-detail', args=(self.user.id,))
#         self.request = factory.get(url)
# 
#     @skip("Broken as of 30b3e784a0fdf82db51c0f0a08dd3b8c3a8d4aec")
#     def test_is_public(self):
#         force_authenticate(self.request, user=self.anonymous_user)
#         response = self.view(self.request, pk=self.image.id)
#         self.assertEquals(response.status_code, 200)
# 
#     def test_is_visible_to_authenticated_user(self):
#         force_authenticate(self.request, user=self.user)
#         response = self.view(self.request, pk=self.image.id)
#         self.assertEquals(response.status_code, 200)
# 
#     def test_response_contains_expected_fields(self):
#         force_authenticate(self.request, user=self.user)
#         response = self.view(self.request, pk=self.image.id)
#         data = response.data
# 
#         self.assertEquals(len(data), 12, "Unexepcted # of arguments in API endpoint")
#         self.assertIn('id', data)
#         self.assertIn('url', data)
#         self.assertIn('uuid', data)
#         self.assertIn('name', data)
#         self.assertIn('description', data)
#         self.assertIn('is_public', data)
#         self.assertIn('icon', data)
#         self.assertIn('tags', data)
#         self.assertIn('created_by', data)
#         self.assertIn('start_date', data)
#         self.assertIn('end_date', data)


class CreateTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('post' not in ViewSet.http_method_names)


class UpdateTests(APITestCase):

    def test_endpoint_does_exist(self):
        self.assertTrue('put' in ViewSet.http_method_names)


class DeleteTests(APITestCase):

    def test_endpoint_does_not_exist(self):
        self.assertTrue('delete' not in ViewSet.http_method_names)
