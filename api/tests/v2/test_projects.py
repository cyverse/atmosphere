from rest_framework.test import APITestCase, APIRequestFactory,\
    force_authenticate
from api.v2.views import ProjectViewSet
from .base import APISanityTestCase
from api.tests.factories import ProjectFactory, UserFactory,\
    AnonymousUserFactory, GroupFactory, GroupMembershipFactory
from django.core.urlresolvers import reverse
from core.models import Project

EXPECTED_FIELD_COUNT = 15


class ProjectTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:project'

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()

        self.user = UserFactory.create()
        self.group = GroupFactory.create(name=self.user.username)
        self.membership = GroupMembershipFactory.create(
            user=self.user,
            group=self.group,
            is_leader=True)
        self.group.user_set.add(self.user)
        self.project = ProjectFactory.create(owner=self.group, created_by=self.user)

        self.user2 = UserFactory.create()
        self.group2 = GroupFactory.create(name=self.user2.username)
        self.membership2 = GroupMembershipFactory.create(
            user=self.user2,
            group=self.group2,
            is_leader=True)
        self.group2.user_set.add(self.user2)
        self.project2 = ProjectFactory.create(owner=self.group2, created_by=self.user2)

        self.not_user = UserFactory.create()
        self.not_group = GroupFactory.create(name=self.not_user.username)
        self.not_membership = GroupMembershipFactory.create(
            user=self.not_user,
            group=self.not_group,
            is_leader=True)
        self.not_group.user_set.add(self.not_user)
        self.not_project = ProjectFactory.create(owner=self.not_group, created_by=self.not_user)

        self.unsaved_project = ProjectFactory.build(owner=self.group, created_by=self.user)

        list_url = reverse('api:v2:project-list')
        detail_url = reverse('api:v2:project-detail', args=(self.project.id,))

        self.create_view = ProjectViewSet.as_view({'post': 'create'})
        self.delete_view = ProjectViewSet.as_view({'delete': 'destroy'})
        self.detail_view = ProjectViewSet.as_view({'get': 'retrieve'})
        self.list_view = ProjectViewSet.as_view({'get': 'list'})
        self.update_view = ProjectViewSet.as_view({'patch': 'partial_update'})

        self.factory = APIRequestFactory()
        self.bad_create_request = self.factory.post(list_url)
        self.create_request = self.factory.post(list_url, {
            'name': self.unsaved_project.name,
            'description': self.unsaved_project.description,
            'owner': self.group.name
        })
        self.delete_request = self.factory.delete(detail_url)
        self.detail_request = self.factory.get(detail_url)
        self.list_request = self.factory.get(list_url)
        self.updated_project_data = {
            'name': 'updated name',
            'description': 'updated description'
        }
        self.update_request = self.factory.patch(detail_url, self.updated_project_data)

    def test_list_is_not_public(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 403)

    def test_list_response_contains_expected_fields(self):
        force_authenticate(self.list_request, user=self.user)
        response = self.list_view(self.list_request)
        data = response.data.get('results')
        self.assertTrue(data, "Response contained no results")
        project_data = data[0]

        self.assertEquals(response.status_code, 200)
        self.assertEquals(
            len(project_data), EXPECTED_FIELD_COUNT,
            "Number of fields does not match (%s != %s)"
            % (len(project_data), EXPECTED_FIELD_COUNT))
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

    def test_detail_is_not_public(self):
        force_authenticate(self.detail_request, user=self.anonymous_user)
        response = self.detail_view(self.detail_request, pk=self.project.id)
        self.assertEquals(response.status_code, 403)

    def test_detail_response_contains_expected_fields(self):
        force_authenticate(self.detail_request, user=self.user)
        response = self.detail_view(self.detail_request, pk=self.project.id)
        data = response.data

        self.assertEquals(response.status_code, 200)
        self.assertEquals(
            len(data), EXPECTED_FIELD_COUNT,
            "Number of fields does not match (%s != %s)" % (len(data), EXPECTED_FIELD_COUNT))
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

    def test_create_project_fails_for_anonymous_user(self):
        force_authenticate(self.create_request, user=self.anonymous_user)
        response = self.create_view(self.create_request)
        self.assertEquals(response.status_code, 403)

    def test_create_project_validation(self):
        force_authenticate(self.bad_create_request, user=self.user)
        response = self.create_view(self.bad_create_request)
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

    def test_create_project_as_authenticated_user(self):
        current_count = Project.objects.count()
        force_authenticate(self.create_request, user=self.user)
        response = self.create_view(self.create_request)
        self.assertEquals(
            response.status_code, 201,
            "Response did not result in a 201-created: (%s) %s"
            % (response.status_code, response.data))
        self.assertEquals(Project.objects.count(), current_count + 1)

    def test_update_project_fails_for_anonymous_user(self):
        force_authenticate(self.update_request, user=self.anonymous_user)
        response = self.update_view(self.update_request)
        self.assertEquals(response.status_code, 403)

    def test_authenticated_user_cannot_update_project_they_do_not_own(self):
        force_authenticate(self.update_request, user=self.user)
        response = self.update_view(self.update_request, pk=self.not_project.id)
        self.assertEquals(
            response.status_code, 404,
            "Encountered an unexpected status_code: (%s) %s"
            % (response.status_code, response.data))

    def test_update_project_for_valid_user(self):
        current_count = Project.objects.count()
        force_authenticate(self.update_request, user=self.user)
        response = self.update_view(self.update_request, pk=self.project.id)
        self.assertEquals(
            response.status_code, 200,
            "Project update failed: (%s) %s" % (response.status_code, response.data))
        self.assertEquals(Project.objects.count(), current_count)
        project = Project.objects.first()
        self.assertEquals(project.name, self.updated_project_data['name'])
        self.assertEquals(
            project.description,
            self.updated_project_data['description'])

    def test_anonymous_user_cannot_delete_project(self):
        force_authenticate(self.delete_request, user=self.anonymous_user)
        response = self.delete_view(self.delete_request)
        self.assertEquals(response.status_code, 403)

    def test_user_cannot_delete_project_they_do_not_own(self):
        force_authenticate(self.delete_request, user=self.not_user)
        response = self.delete_view(self.delete_request, pk=self.project.id)
        self.assertEquals(response.status_code, 404)

    def test_user_can_delete_project_they_own(self):
        force_authenticate(self.delete_request, user=self.user)
        response = self.delete_view(self.delete_request, pk=self.project.id)
        self.assertEquals(response.status_code, 204)
