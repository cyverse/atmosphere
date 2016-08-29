from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.v2.views import TagViewSet
from api.tests.factories import TagFactory, UserFactory, AnonymousUserFactory
from django.core.urlresolvers import reverse
from core.models import Tag


class GetTagListTests(APITestCase):

    def setUp(self):
        self.tags = TagFactory.create_batch(10)
        self.view = TagViewSet.as_view({'get': 'list'})
        self.anonymous_user = AnonymousUserFactory()

        factory = APIRequestFactory()
        url = reverse('api:v2:tag-list')
        self.request = factory.get(url)

    def test_does_not_require_authenticated_user(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 200)

    def test_response_is_paginated(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.data['count'], len(self.tags))
        self.assertEquals(len(response.data.get('results')), len(self.tags))

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        data = response.data.get('results')[0]

        self.assertEquals(len(data), 6)
        self.assertEquals(data['id'], self.tags[0].id)
        self.assertEquals(data['uuid'], str(self.tags[0].uuid))
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.tags[0].name)
        self.assertEquals(data['description'], self.tags[0].description)
        self.assertTrue(data['allow_access'])


class GetTagDetailTests(APITestCase):

    def setUp(self):
        self.tag = TagFactory.create()
        self.view = TagViewSet.as_view({'get': 'retrieve'})
        self.anonymous_user = AnonymousUserFactory()
        factory = APIRequestFactory()
        url = reverse('api:v2:tag-detail', args=(self.tag.id,))
        self.request = factory.get(url)

    def test_does_not_require_authenticated_user(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request, pk=self.tag.id)
        self.assertEquals(response.status_code, 200)

    def test_response_contains_expected_fields(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request, pk=self.tag.id)
        data = response.data

        self.assertEquals(len(data), 6)
        self.assertEquals(data['id'], self.tag.id)
        self.assertEquals(data['uuid'], str(self.tag.uuid))
        self.assertIn('url', data)
        self.assertEquals(data['name'], self.tag.name)
        self.assertEquals(data['description'], self.tag.description)
        self.assertTrue(data['allow_access'])


class DeleteTagTests(APITestCase):

    def setUp(self):
        self.tag = TagFactory.create()
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory()
        self.staff_user = UserFactory(is_staff=True)

        factory = APIRequestFactory()
        url = reverse('api:v2:tag-detail', args=(self.tag.id,))
        self.request = factory.delete(url)

        self.view = TagViewSet.as_view({'delete': 'destroy'})

    def test_anonymous_user_cannot_delete_tag(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_non_staff_user_cannot_delete_tag(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_staff_user_can_delete_tag(self):
        force_authenticate(self.request, user=self.staff_user)
        response = self.view(self.request, pk=self.tag.id)
        self.assertEquals(response.status_code, 204)


class CreateTagTests(APITestCase):

    def setUp(self):
        self.tag = TagFactory.build()
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.staff_user = UserFactory.create(is_staff=True)

        self.factory = APIRequestFactory()
        self.url = reverse('api:v2:tag-list')
        self.request = self.factory.post(self.url, {
            'name': self.tag.name,
            'description': self.tag.description
        })

        self.view = TagViewSet.as_view({'post': 'create'})

    def test_anonymous_user_cannot_create_tag(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_required_fields(self):
        bad_request = self.factory.post(self.url)
        force_authenticate(bad_request, user=self.user)
        response = self.view(bad_request)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(len(response.data), 2)
        self.assertIn('name', response.data)
        self.assertIn('description', response.data)

    def test_authenticated_user_can_create_tag(self):
        self.assertEquals(Tag.objects.count(), 0)
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 201)
        self.assertEquals(Tag.objects.count(), 1)
        tag = Tag.objects.first()
        self.assertEquals(tag.user, self.user)


class UpdateTagTests(APITestCase):

    def setUp(self):
        self.tag = TagFactory.create()
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.staff_user = UserFactory.create(is_staff=True)
        self.updated_tag_data = {
            'name': 'new-tag-name',
            'description': 'new tag description'
        }

        self.factory = APIRequestFactory()
        self.url = reverse('api:v2:tag-detail', args=(self.tag.id,))
        self.request = self.factory.put(self.url, {
            'name': self.updated_tag_data['name'],
            'description': self.updated_tag_data['description']
        })

        self.view = TagViewSet.as_view({'put': 'update'})

    def test_anonymous_user_cannot_update_tag(self):
        force_authenticate(self.request, user=self.anonymous_user)
        response = self.view(self.request)
        self.assertEquals(response.status_code, 403)

    def test_authenticated_user_cannot_update_tag(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, pk=self.tag.id)
        self.assertEquals(response.status_code, 403)

    def test_staff_user_can_update_tag(self):
        self.assertEquals(Tag.objects.count(), 1)
        force_authenticate(self.request, user=self.staff_user)
        response = self.view(self.request, pk=self.tag.id)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(Tag.objects.count(), 1)
        tag = Tag.objects.first()
        self.assertEquals(tag.name, self.updated_tag_data['name'])
        self.assertEquals(
            tag.description,
            self.updated_tag_data['description'])
