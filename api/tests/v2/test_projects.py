from rest_framework.test import APITestCase, APIRequestFactory,\
    force_authenticate
from api.v2.views import ProjectViewSet
from api.tests.factories import ProjectFactory, UserFactory,\
    AnonymousUserFactory, GroupFactory, GroupMembershipFactory
from django.core.urlresolvers import reverse
from core.models import Project


class GetProjectListTests(APITestCase):

    def setUp(self):
        self.expected_field_count = 15
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.membership = GroupMembershipFactory.create(
            user=self.user,
            group=self.group,
            is_leader=True)
        self.project = ProjectFactory.create(owner=self.group, created_by=self.user)

        user2 = UserFactory.create()
        group2 = GroupFactory.create(name=user2.username)
        project2 = ProjectFactory.create(owner=group2, created_by=user2)

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
        data = response.data.get('results')
        self.assertTrue(data, "Response contained no results")
        project_data = data[0]

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(project_data), self.expected_field_count, "Number of fields does not match (%s != %s)" % (len(project_data), self.expected_field_count))
        self.assertEquals(project_data['id'], self.project.id)
        self.assertIn('url', project_data)
        self.assertEquals(project_data['name'], self.project.name)
        self.assertEquals(project_data['description'], self.project.description)
        self.assertIn('created_by', project_data)
        self.assertIn('owner', project_data)
        self.assertIn('users', project_data)
        self.assertIn('leaders', project_data)
        self.assertIn('uuid', project_data)
        self.assertIn('instances', project_data)
        self.assertIn('volumes', project_data)
        self.assertIn('images', project_data)
        self.assertIn('links', project_data)
        self.assertIn('start_date', project_data)
        self.assertIn('end_date', project_data)


class GetProjectDetailTests(APITestCase):

    def setUp(self):
        self.expected_field_count = 15
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.membership = GroupMembershipFactory.create(
            user=self.user,
            group=self.group,
            is_leader=True)
        self.project = ProjectFactory.create(owner=self.group, created_by=self.user)

        user2 = UserFactory.create()
        group2 = GroupFactory.create(name=user2.username)
        ProjectFactory.create(owner=group2, created_by=user2)

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
        self.assertEquals(len(data), self.expected_field_count, "Number of fields does not match (%s != %s)" % (len(data), self.expected_field_count))
        self.assertEquals(data['id'], self.project.id)
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.project.name)
        self.assertEquals(data['description'], self.project.description)
        self.assertIn('created_by', data)
        self.assertIn('owner', data)
        self.assertIn('users', data)
        self.assertIn('leaders', data)
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
        self.group.user_set.add(self.user)
        self.membership = GroupMembershipFactory.create(
            user=self.user,
            group=self.group,
            is_leader=True)
        self.project = ProjectFactory.build(owner=self.group, created_by=self.user)

        self.view = ProjectViewSet.as_view({'post': 'create'})
        self.factory = APIRequestFactory()
        self.url = reverse('api:v2:project-list')
        self.request = self.factory.post(self.url, {
            'name': self.project.name,
            'description': self.project.description,
            'owner': self.group.name
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
        self.assertEquals(
            len(data), 2,
            "Unexpected error response: %s" % data)
        self.assertIn(
            'name', data,
            "Unexpected error response: %s" % data)
        self.assertIn(
            'owner', data,
            "Unexpected error response: %s" % data)
        self.assertEquals(
            data['owner'], [u'This field is required.'],
            "Unexpected error response: %s" % data)
        self.assertEquals(
            data['name'], [u'This field is required.'],
            "Unexpected error response: %s" % data)

    def test_authenticated_user_can_create_project(self):
        self.assertEquals(Project.objects.count(), 0)
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 201,
            "Response did not result in a 201-created: (%s) %s"
            % (response.status_code, response.data))
        self.assertEquals(Project.objects.count(), 1)
        project = Project.objects.first()
        self.assertEquals(project.owner, self.group)


class UpdateProjectTests(APITestCase):

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.membership = GroupMembershipFactory.create(
            user=self.user,
            group=self.group,
            is_leader=True)
        self.project = ProjectFactory.create(owner=self.group, created_by=self.user)

        self.not_user = UserFactory.create()
        self.not_group = GroupFactory.create(name=self.not_user.username)
        self.not_project = ProjectFactory.create(owner=self.not_group, created_by=self.not_user)

        self.updated_project_data = {
            'name': 'updated name',
            'description': 'updated description'
        }

        self.factory = APIRequestFactory()
        self.url = reverse('api:v2:project-detail', args=(self.project.id,))
        self.request = self.factory.patch(self.url, {
            'name': self.updated_project_data['name'],
            'description': self.updated_project_data['description']
        })

        self.view = ProjectViewSet.as_view({'patch': 'partial_update'})

    def test_anonymous_user_cannot_update_project(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_authenticated_user_cannot_update_project_they_do_not_own(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.not_project.id)
        self.assertEquals(response.status_code, 404,
            "Encountered an unexpected status_code: (%s) %s" % (response.status_code, response.data))

    def test_user_can_update_project(self):
        self.assertEquals(Project.objects.count(), 2)
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.project.id)
        self.assertEquals(
            response.status_code, 200,
            "Project update failed: (%s) %s" % (response.status_code, response.data))
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
        self.membership = GroupMembershipFactory.create(
            user=self.user,
            group=self.group,
            is_leader=True)
        self.project = ProjectFactory.create(owner=self.group, created_by=self.user)

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
