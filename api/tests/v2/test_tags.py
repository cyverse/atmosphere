from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import TagViewSet
from api.tests.factories import TagFactory, UserFactory, AnonymousUserFactory
from django.core.urlresolvers import reverse
from core.models import Tag

from .base import APISanityTestCase

EXPECTED_FIELD_COUNT = 6

class TagTests(APITestCase, APISanityTestCase):
    url_route = "api:v2:tag"

    def setUp(self):
        self.tags = TagFactory.create_batch(10)
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory()
        self.staff_user = UserFactory(is_staff=True)

        self.tag = TagFactory.create()
        self.unsaved_tag = TagFactory.build()
        self.updated_tag_data = {
            'name': 'new-tag-name',
            'description': 'new tag description'
        }

        self.factory = APIRequestFactory()


        self.create_view = TagViewSet.as_view({'post': 'create'})
        self.delete_view = TagViewSet.as_view({'delete': 'destroy'})
        self.detail_view = TagViewSet.as_view({'get': 'retrieve'})
        self.list_view = TagViewSet.as_view({'get': 'list'})
        self.update_view = TagViewSet.as_view({'put': 'update'})

        detail_url = reverse(self.url_route + '-detail', args=(self.tag.id,))
        list_url = reverse(self.url_route + '-list')

        self.create_request = self.factory.post(list_url, {
            'name': self.unsaved_tag.name,
            'description': self.unsaved_tag.description
        })
        self.delete_request = self.factory.delete(detail_url)
        self.detail_request = self.factory.get(detail_url)
        self.list_request = self.factory.get(list_url)
        self.update_request = self.factory.put(detail_url, {
            'name': self.updated_tag_data['name'],
            'description': self.updated_tag_data['description']
        })

    def test_list_does_not_require_authenticated_user(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        self.assertEquals(response.status_code, 200)

    def test_list_response_is_paginated(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        current_count = Tag.objects.count()
        self.assertEquals(response.data['count'], current_count)
        self.assertEquals(len(response.data.get('results')), current_count)

    def test_list_response_contains_expected_fields(self):
        force_authenticate(self.list_request, user=self.anonymous_user)
        response = self.list_view(self.list_request)
        data = response.data.get('results')[0]

        self.assertEquals(
            len(data), EXPECTED_FIELD_COUNT,
            "The number of arguments has changed for GET /tags (%s!=%s)"
            % (len(data), EXPECTED_FIELD_COUNT)
        )
        self.assertEquals(data['id'], self.tags[0].id)
        self.assertEquals(data['uuid'], str(self.tags[0].uuid))
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.tags[0].name)
        self.assertEquals(data['description'], self.tags[0].description)
        self.assertTrue(data['allow_access'])

    def test_detail_does_not_require_authenticated_user(self):
        force_authenticate(self.detail_request, user=self.anonymous_user)
        response = self.detail_view(self.detail_request, pk=self.tag.id)
        self.assertEquals(response.status_code, 200)

    def test_detail_response_contains_expected_fields(self):
        force_authenticate(self.detail_request, user=self.anonymous_user)
        response = self.detail_view(self.detail_request, pk=self.tag.id)
        data = response.data

        self.assertEquals(
            len(data), EXPECTED_FIELD_COUNT,
            "The number of arguments has changed for GET /tags/%s (%s!=%s)"
            % (self.tag.id, len(data), EXPECTED_FIELD_COUNT)
        )
        self.assertEquals(data['id'], self.tag.id)
        self.assertEquals(data['uuid'], str(self.tag.uuid))
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.tag.name)
        self.assertEquals(data['description'], self.tag.description)
        self.assertTrue(data['allow_access'])

    def test_anonymous_user_cannot_delete_tag(self):
        force_authenticate(self.delete_request, user=self.anonymous_user)
        response = self.delete_view(self.delete_request)
        self.assertEquals(response.status_code, 403)

    def test_non_staff_user_cannot_delete_tag(self):
        force_authenticate(self.delete_request, user=self.user)
        response = self.delete_view(self.delete_request)
        self.assertEquals(response.status_code, 403)

    def test_staff_user_can_delete_tag(self):
        force_authenticate(self.delete_request, user=self.staff_user)
        response = self.delete_view(self.delete_request, pk=self.tag.id)
        self.assertEquals(response.status_code, 204)

    def test_anonymous_user_cannot_create_tag(self):
        force_authenticate(self.create_request, user=self.anonymous_user)
        response = self.create_view(self.create_request)
        self.assertEquals(response.status_code, 403)

    def test_required_fields_on_create_tag(self):
        create_url = reverse(self.url_route + '-list')
        bad_request = self.factory.post(create_url)
        force_authenticate(bad_request, user=self.user)
        response = self.create_view(bad_request)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(len(response.data), 2)
        self.assertIn('name', response.data)
        self.assertIn('description', response.data)

    def test_authenticated_user_can_create_tag(self):
        current_count = Tag.objects.count()
        force_authenticate(self.create_request, user=self.user)
        response = self.create_view(self.create_request)
        self.assertEquals(
            response.status_code, 201,
            "Expected 201-response. Received (%s): %s"
            % (response.status_code, response.data))
        self.assertIn('id', response.data,
            "Expected new tag ID as part of 201 response. Recieved: %s"
            % response.data)
        tag_id = response.data.get('id')
        self.assertEquals(Tag.objects.count(), current_count + 1)
        tag = Tag.objects.get(id=tag_id)
        self.assertEquals(tag.user, self.user)

    def test_anonymous_user_cannot_update_tag(self):
        force_authenticate(self.update_request, user=self.anonymous_user)
        response = self.update_view(self.update_request)
        self.assertEquals(response.status_code, 403)

    def test_authenticated_user_cannot_update_tag(self):
        force_authenticate(self.update_request, user=self.user)
        response = self.update_view(self.update_request, pk=self.tag.id)
        self.assertEquals(response.status_code, 403)

    def test_staff_user_can_update_tag(self):
        current_count = Tag.objects.count()
        force_authenticate(self.update_request, user=self.staff_user)
        response = self.update_view(self.update_request, pk=self.tag.id)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(Tag.objects.count(), current_count)
        tag = Tag.objects.get(id=self.tag.id)
        self.assertEquals(tag.name, self.updated_tag_data['name'])
        self.assertEquals(
            tag.description,
            self.updated_tag_data['description'])
