import itertools
from unittest import skip
from django.core import urlresolvers
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.test import APITestCase, force_authenticate

from api.tests.factories import (
    UserFactory, AnonymousUserFactory, IdentityFactory, ProviderFactory, AllocationSourceFactory,
    UserAllocationSourceFactory
)
from api.v2.views import AllocationSourceViewSet as ViewSet


class AllocationSourceTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user_without_sources = UserFactory.create(username='test-username')
        self.user_with_sources = UserFactory.create(username='test-username-with-sources')
        self.provider = ProviderFactory.create()
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user_without_sources,
            provider=self.provider)
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user_with_sources,
            provider=self.provider)

        self.allocation_source_1 = AllocationSourceFactory.create(name='TG-TRA110001',
                                                                  source_id='110001',
                                                                  compute_allowed=1000)

        self.allocation_source_2 = AllocationSourceFactory.create(name='TG-TRA220002',
                                                                  source_id='220002',
                                                                  compute_allowed=2000)

        self.allocation_source_3 = AllocationSourceFactory.create(name='TG-TRA330003',
                                                                  source_id='330003',
                                                                  compute_allowed=3000)

        UserAllocationSourceFactory.create(user=self.user_with_sources, allocation_source=self.allocation_source_1)
        UserAllocationSourceFactory.create(user=self.user_with_sources, allocation_source=self.allocation_source_2)

    def test_can_create_allocation_source(self):
        """Can I even create an allocation source?"""
        client = APIClient()
        client.force_authenticate(user=self.user_without_sources)
        allocation_source = AllocationSourceFactory.create(name='TG-TRA990001',
                                                           source_id='990001',
                                                           compute_allowed=9000)
        expected_values = {
            'name': 'TG-TRA990001',
            'source_id': '990001',
            'compute_allowed': 9000
        }
        self.assertDictContainsSubset(expected_values, allocation_source.__dict__)

    def test_anonymous_user_cant_see_allocation_sources(self):
        request_factory = APIRequestFactory()
        list_view = ViewSet.as_view({'get': 'list'})
        url = urlresolvers.reverse('api:v2:allocationsource-list')
        self.assertEqual(url, '/api/v2/allocation_sources')
        request = request_factory.get(url)
        force_authenticate(request, user=self.anonymous_user)
        response = list_view(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.status_text, 'Forbidden')

    def test_loggedin_user_with_no_sources_cant_see_allocation_sources(self):
        request_factory = APIRequestFactory()
        list_view = ViewSet.as_view({'get': 'list'})
        url = urlresolvers.reverse('api:v2:allocationsource-list')
        self.assertEqual(url, '/api/v2/allocation_sources')
        request = request_factory.get(url)
        force_authenticate(request, user=self.user_without_sources)
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_text, 'OK')
        self.assertEqual(response.data['count'], 0)

    def test_loggedin_user_can_list_allocation_sources(self):
        request_factory = APIRequestFactory()
        list_view = ViewSet.as_view({'get': 'list'})
        url = urlresolvers.reverse('api:v2:allocationsource-list')
        self.assertEqual(url, '/api/v2/allocation_sources')
        request = request_factory.get(url)
        force_authenticate(request, user=self.user_with_sources)
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_text, 'OK')
        expected_values = [
            {
                'name': 'TG-TRA110001',
                'source_id': '110001',
                'compute_allowed': 1000
            },
            {
                'name': 'TG-TRA220002',
                'source_id': '220002',
                'compute_allowed': 2000
            }
        ]
        self.assertEqual(response.data['count'], len(expected_values))
        for allocation_source, expected_dict in itertools.izip_longest(expected_values, response.data['results']):
            self.assertDictContainsSubset(allocation_source, expected_dict)

    @skip('TODO: Figure out why it fails')
    def test_loggedin_user_can_get_allocation_source(self):
        request_factory = APIRequestFactory()
        retrieve_view = ViewSet.as_view({'get': 'retrieve'})
        url = urlresolvers.reverse('api:v2:allocationsource-detail', args=(self.allocation_source_1.id,))
        self.assertEqual(url, '/api/v2/allocation_sources/{}'.format(self.allocation_source_1.id))
        request = request_factory.get(url)
        force_authenticate(request, user=self.user_with_sources)
        response = retrieve_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_text, 'OK')
