from rest_framework.test import APITestCase, APIRequestFactory,\
    force_authenticate
from api.v2.views import ProjectViewSet
from api.tests.factories import ProjectFactory, UserFactory,\
    AnonymousUserFactory, GroupFactory
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
        url = reverse('api:v2:project-list')
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
        self.assertEquals(len(data), 12, "Number of fields does not match")
        self.assertEquals(data['id'], self.project.id)
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.project.name)
        self.assertEquals(data['description'], self.project.description)
        self.assertIn('owner', data)
        self.assertIn('uuid', data)
        self.assertIn('instances', data)
        self.assertIn('volumes', data)
        self.assertIn('images', data)
        self.assertIn('links', data)
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
        url = reverse('api:v2:project-detail', args=(self.project.id,))
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
        self.assertEquals(len(data), 12, "Number of fields does not match")
        self.assertEquals(data['id'], self.project.id)
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.project.name)
        self.assertEquals(data['description'], self.project.description)
        self.assertIn('owner', data)
        self.assertIn('uuid', data)
        self.assertIn('instances', data)
        self.assertIn('volumes', data)
        self.assertIn('images', data)
        self.assertIn('links', data)
        self.assertIn('start_date', data)
        self.assertIn('end_date', data)


class CreateProjectTests(APITestCase):

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.project = ProjectFactory.build(owner=self.group)

        self.view = ProjectViewSet.as_view({'post': 'create'})
        self.factory = APIRequestFactory()
        self.url = reverse('api:v2:project-list')
        self.request = self.factory.post(self.url, {
            'name': self.project.name,
            'description': self.project.description
        })

    def test_anonymous_user_cannot_create_project(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_required_fields(self):
        bad_request = self.factory.post(self.url)
        force_authenticate(bad_request, user=self.user)
        response = self.view(bad_request)
        data = response.data

        self.assertEquals(response.status_code, 400)
        self.assertEquals(len(data), 1)
        self.assertIn('name', data)

    def test_authenticated_user_can_create_project(self):
        self.assertEquals(Project.objects.count(), 0)
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 201)
        self.assertEquals(Project.objects.count(), 1)
        project = Project.objects.first()
        self.assertEquals(project.owner, self.group)


class UpdateProjectTests(APITestCase):

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.project = ProjectFactory.create(owner=self.group)

        self.not_user = UserFactory.create()
        self.not_group = GroupFactory.create(name=self.not_user.username)
        self.not_project = ProjectFactory.create(owner=self.not_group)

        self.updated_project_data = {
            'name': 'updated name',
            'description': 'updated description'
        }

        self.factory = APIRequestFactory()
        self.url = reverse('api:v2:project-detail', args=(self.project.id,))
        self.request = self.factory.put(self.url, {
            'name': self.updated_project_data['name'],
            'description': self.updated_project_data['description']
        })

        self.view = ProjectViewSet.as_view({'put': 'update'})

    def test_anonymous_user_cannot_update_project(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_authenticated_user_cannot_update_project_they_do_not_own(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.not_project.id)
        self.assertEquals(response.status_code, 404)

    def test_user_can_update_project(self):
        self.assertEquals(Project.objects.count(), 2)
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.project.id)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(Project.objects.count(), 2)
        project = Project.objects.first()
        self.assertEquals(project.name, self.updated_project_data['name'])
        self.assertEquals(
            project.description,
            self.updated_project_data['description'])


class DeleteProjectTests(APITestCase):

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.project = ProjectFactory.create(owner=self.group)

        self.not_user = UserFactory.create()
        self.not_group = GroupFactory.create(name=self.not_user.username)

        self.view = ProjectViewSet.as_view({'delete': 'destroy'})
        self.factory = APIRequestFactory()
        self.url = reverse('api:v2:project-detail', args=(self.project.id,))
        self.request = self.factory.delete(self.url)

    def test_anonymous_user_cannot_delete_project(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_user_cannot_delete_project_they_do_not_own(self):
        force_authenticate(self.request, user=self.not_user)
        response = self.view(self.request, pk=self.project.id)
        self.assertEquals(response.status_code, 404)

    def test_user_can_delete_project_they_own(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.project.id)
        self.assertEquals(response.status_code, 204)
