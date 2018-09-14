import decimal
import itertools
import uuid
from unittest import skip
from django.core import urlresolvers
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.test import APITestCase, force_authenticate

from api.tests.factories import (
    UserFactory, AnonymousUserFactory, IdentityFactory, ProviderFactory,
    AllocationSourceFactory, UserAllocationSourceFactory
)
from cyverse_allocation.tasks import update_snapshot_cyverse
from .base import APISanityTestCase
from api.v2.views import AllocationSourceViewSet as ViewSet


class AllocationSourceTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:allocationsource'

    def setUp(self):
        self.list_view = ViewSet.as_view({'get': 'list'})
        self.detailed_view = ViewSet.as_view({'get': 'retrieve'})

        self.anonymous_user = AnonymousUserFactory()
        self.user_without_sources = UserFactory.create(username='test-username')
        self.user_with_sources = UserFactory.create(
            username='test-username-with-sources'
        )
        self.user = self.user_with_sources
        self.provider = ProviderFactory.create()
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user_without_sources, provider=self.provider
        )
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user_with_sources, provider=self.provider
        )

        self.allocation_source_1 = AllocationSourceFactory.create(
            name='TG-TRA110001', compute_allowed=1000
        )

        self.allocation_source_2 = AllocationSourceFactory.create(
            name='TG-TRA220002', compute_allowed=2000
        )

        self.allocation_source_3 = AllocationSourceFactory.create(
            name='TG-TRA330003', compute_allowed=3000
        )

        UserAllocationSourceFactory.create(
            user=self.user_with_sources,
            allocation_source=self.allocation_source_1
        )
        UserAllocationSourceFactory.create(
            user=self.user_with_sources,
            allocation_source=self.allocation_source_2
        )

    def test_can_create_allocation_source(self):
        """Can I even create an allocation source?"""
        client = APIClient()
        client.force_authenticate(user=self.user_without_sources)
        allocation_source = AllocationSourceFactory.create(
            name='TG-TRA990001', compute_allowed=9000
        )
        expected_values = {'name': 'TG-TRA990001', 'compute_allowed': 9000}
        self.assertDictContainsSubset(
            expected_values, allocation_source.__dict__
        )

    def test_can_create_infinite_allocation_source(self):
        """Can I create an allocation source with infinite compute_allowed"""
        client = APIClient()
        client.force_authenticate(user=self.user_without_sources)
        payload = {
            'uuid': str(uuid.uuid4()),
            'allocation_source_name': 'TG-INF990002',
            'compute_allowed': -1,
            'renewal_strategy': 'default'
        }

        from core.models import EventTable, AllocationSource, AllocationSourceSnapshot
        creation_event = EventTable(
            name='allocation_source_created_or_renewed',
            entity_id=payload['allocation_source_name'],
            payload=payload
        )

        creation_event.save()

        allocation_source = AllocationSource.objects.get(name='TG-INF990002')
        expected_values = {'name': 'TG-INF990002', 'compute_allowed': -1}
        self.assertDictContainsSubset(
            expected_values, allocation_source.__dict__
        )
        assert isinstance(allocation_source, AllocationSource)
        self.assertEqual(allocation_source.compute_allowed, -1)
        update_snapshot_cyverse()
        self.assertEqual(
            allocation_source.time_remaining(), decimal.Decimal('Infinity')
        )
        self.assertEqual(allocation_source.is_over_allocation(), False)
        allocation_snapshot = allocation_source.snapshot
        assert isinstance(allocation_snapshot, AllocationSourceSnapshot)
        self.assertEqual(allocation_snapshot.compute_allowed, -1)
        self.assertEqual(allocation_snapshot.compute_used, 0)
        allocation_snapshot.compute_used = 9999999
        allocation_snapshot.save()
        self.assertEqual(
            allocation_source.time_remaining(), decimal.Decimal('Infinity')
        )
        self.assertEqual(allocation_source.is_over_allocation(), False)

    def test_renewal_rules(self):
        """Check renewal rules"""
        import datetime
        from business_rules import run_all
        from django.utils import timezone
        from cyverse_allocation.cyverse_rules_engine_setup import CyverseTestRenewalVariables, \
            CyverseTestRenewalActions, cyverse_rules
        from core.models import EventTable

        source_01 = AllocationSourceFactory.create(
            uuid='98e9aed3-1f4c-415c-9ea3-618a8c318eaa',
            name='default_source_01',
            compute_allowed=168,
            start_date=datetime.datetime(
                2017, 7, 4, hour=12, tzinfo=timezone.utc
            ),
            end_date=None,
            renewal_strategy='default'
        )

        renewal_events_count_before = EventTable.objects.filter(
            name='allocation_source_created_or_renewed'
        ).count()
        self.assertEqual(renewal_events_count_before, 0)

        current_time = datetime.datetime(
            2017, 7, 5, hour=12, tzinfo=timezone.utc
        )
        run_all(
            rule_list=cyverse_rules,
            defined_variables=CyverseTestRenewalVariables(
                source_01,
                current_time=current_time,
                last_renewal_event_date=source_01.start_date
            ),
            defined_actions=CyverseTestRenewalActions(
                source_01, current_time=current_time
            )
        )

        renewal_events_count_after_one = EventTable.objects.filter(
            name='allocation_source_created_or_renewed'
        ).count()
        self.assertEqual(renewal_events_count_after_one, 0)

        current_time = datetime.datetime(
            2017, 8, 1, hour=12, tzinfo=timezone.utc
        )
        run_all(
            rule_list=cyverse_rules,
            defined_variables=CyverseTestRenewalVariables(
                source_01,
                current_time=current_time,
                last_renewal_event_date=source_01.start_date
            ),
            defined_actions=CyverseTestRenewalActions(
                source_01, current_time=current_time
            )
        )

        renewal_events_count_after_two = EventTable.objects.filter(
            name='allocation_source_created_or_renewed'
        ).count()
        self.assertEqual(renewal_events_count_after_two, 1)
        last_renewal_event_date = current_time

        current_time = datetime.datetime(
            2017, 8, 3, hour=12, tzinfo=timezone.utc
        )
        run_all(
            rule_list=cyverse_rules,
            defined_variables=CyverseTestRenewalVariables(
                source_01,
                current_time=current_time,
                last_renewal_event_date=last_renewal_event_date
            ),
            defined_actions=CyverseTestRenewalActions(
                source_01, current_time=current_time
            )
        )

        renewal_events_count_after_three = EventTable.objects.filter(
            name='allocation_source_created_or_renewed'
        ).count()
        self.assertEqual(renewal_events_count_after_three, 1)

        current_time = datetime.datetime(
            2017, 9, 1, hour=12, tzinfo=timezone.utc
        )
        run_all(
            rule_list=cyverse_rules,
            defined_variables=CyverseTestRenewalVariables(
                source_01,
                current_time=current_time,
                last_renewal_event_date=last_renewal_event_date
            ),
            defined_actions=CyverseTestRenewalActions(
                source_01, current_time=current_time
            )
        )

        renewal_events_count_after_four = EventTable.objects.filter(
            name='allocation_source_created_or_renewed'
        ).count()
        self.assertEqual(renewal_events_count_after_four, 2)

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
                'compute_allowed': 1000
            }, {
                'name': 'TG-TRA220002',
                'compute_allowed': 2000
            }
        ]
        self.assertEqual(response.data['count'], len(expected_values))
        for allocation_source, expected_dict in itertools.izip_longest(
            expected_values, response.data['results']
        ):
            self.assertDictContainsSubset(allocation_source, expected_dict)

    @skip('TODO: Figure out why it fails')
    def test_loggedin_user_can_get_allocation_source(self):
        request_factory = APIRequestFactory()
        retrieve_view = ViewSet.as_view({'get': 'retrieve'})
        url = urlresolvers.reverse(
            'api:v2:allocationsource-detail',
            args=(self.allocation_source_1.id, )
        )
        self.assertEqual(
            url,
            '/api/v2/allocation_sources/{}'.format(self.allocation_source_1.id)
        )
        request = request_factory.get(url)
        force_authenticate(request, user=self.user_with_sources)
        response = retrieve_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_text, 'OK')
