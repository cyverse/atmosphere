from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import ProjectViewSet
from .factories import ProjectFactory, UserFactory, AnonymousUserFactory, GroupFactory
from django.core.urlresolvers import reverse
from core.models import Project


class GetProjectListTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.project = ProjectFactory.create(owner=self.group)

        user2 = UserFactory.create()
        group2 = GroupFactory.create(name=user2.username)
        ProjectFactory.create(owner=group2)

        self.view = ProjectViewSet.as_view({'get': 'list'})
        factory = APIRequestFactory()
        url = reverse('api_v2:project-list')
        self.request = factory.get(url)

    def test_is_not_public(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_response_is_paginated(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        self.assertEquals(response.data['count'], 1)
        self.assertEquals(len(response.data.get('results')), 1)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        data = response.data.get('results')[0]

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data), 8)
        self.assertEquals(data['id'], self.project.id)
        self.assertEquals(data['name'], self.project.name)
        self.assertEquals(data['description'], self.project.description)
        self.assertIn('owner', data)
        self.assertIn('instances', data)
        self.assertIn('volumes', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)


class GetProjectDetailTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.project = ProjectFactory.create(owner=self.group)

        user2 = UserFactory.create()
        group2 = GroupFactory.create(name=user2.username)
        ProjectFactory.create(owner=group2)

        self.view = ProjectViewSet.as_view({'get': 'retrieve'})
        factory = APIRequestFactory()
        url = reverse('api_v2:project-detail', args=(self.project.id,))
        self.request = factory.get(url)

    def test_is_not_public(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request, pk=self.project.id)
        self.assertEquals(response.status_code, 403)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.project.id)
        data = response.data

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(data), 8)
        self.assertEquals(data['id'], self.project.id)
        self.assertEquals(data['name'], self.project.name)
        self.assertEquals(data['description'], self.project.description)
        self.assertIn('owner', data)
        self.assertIn('instances', data)
        self.assertIn('volumes', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)