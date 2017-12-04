import uuid
from django.core.urlresolvers import reverse

from rest_framework.test import APIClient, APITestCase
from core.events.serializers.instance_playbook_history import InstancePlaybookHistoryUpdatedSerializer
from api.tests.factories import (
    UserFactory, AnonymousUserFactory, InstanceFactory,
    ProviderMachineFactory)
from api.v2.views import InstancePlaybookHistoryViewSet, InstancePlaybookViewSet


def common_setup(api_test_case):
    api_test_case.anonymous_user = AnonymousUserFactory()
    api_test_case.user_1 = UserFactory.create(username='test-username')
    api_test_case.user_2 = UserFactory.create(username='not-test-username')
    api_test_case.provider_machine = ProviderMachineFactory()
    api_test_case.instance_1 = InstanceFactory(
        provider_alias=str(uuid.uuid4()),
        name="Instance in active",
        created_by=api_test_case.user_1,
        source=api_test_case.provider_machine.instance_source
    )
    api_test_case.instance_2 = InstanceFactory(
        provider_alias=str(uuid.uuid4()),
        name="Instance in active",
        created_by=api_test_case.user_2,
        source=api_test_case.provider_machine.instance_source
    )
    serializer = InstancePlaybookHistoryUpdatedSerializer(
        data={
            'instance': api_test_case.instance_1.provider_alias,
            'playbook': 'add_user.yml',
            "arguments": {'ATMOUSERNAME':'sgregory'},
            "status": 'queued',
            "message": ""
        }
    )
    if not serializer.is_valid():
        raise Exception('Error creating event 1: %s' % serializer.errors)
    api_test_case.event_1 = serializer.save()
    serializer = InstancePlaybookHistoryUpdatedSerializer(
        data={
            'instance': api_test_case.instance_1.provider_alias,
            'playbook': 'add_user.yml',
            "arguments": {'ATMOUSERNAME':'lenards'},
            "status": 'queued',
            "message": ""
        }
    )
    if not serializer.is_valid():
        raise Exception('Error creating event 2: %s' % serializer.errors)
    api_test_case.event_2 = serializer.save()
    serializer = InstancePlaybookHistoryUpdatedSerializer(
        data={
            'instance': api_test_case.instance_1.provider_alias,
            'playbook': 'add_user.yml',
            "arguments": {'ATMOUSERNAME':'sgregory'},
            "status": 'running',
            "message": ""
        }
    )
    if not serializer.is_valid():
        raise Exception('Error creating event 3: %s' % serializer.errors)
    api_test_case.event_3 = serializer.save()
    serializer = InstancePlaybookHistoryUpdatedSerializer(
        data={
            'instance': api_test_case.instance_2.provider_alias,
            'playbook': 'add_user.yml',
            "arguments": {'ATMOUSERNAME':'sgregory'},
            "status": 'queued',
            "message": ""
        }
    )
    if not serializer.is_valid():
        raise Exception('Error creating event 4: %s' % serializer.errors)
    api_test_case.event_4 = serializer.save()


class InstancePlaybookTests(APITestCase):
    def setUp(self):
        common_setup(self)
        self.list_view = InstancePlaybookViewSet.as_view({'get': 'list'})
        self.url_route = 'api:v2:instance_playbook'
        self.list_url = reverse(self.url_route+"-list")

    def test_valid_list(self):
        client = APIClient()

        client.force_authenticate(user=self.user_1)
        response = client.get(self.list_url)
        data = response.data.get('results')
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertEquals(
            len(data), 2,
            "Expected results mismatch (%s!=%s): %s"
            % (len(data), 2, response.data))
        first_result = data[0]
        self.assertIn('instance', first_result)
        self.assertIn('playbook_arguments', first_result)
        self.assertIn('playbook_name', first_result)
        self.assertIn('status', first_result)

        client.force_authenticate(user=self.user_2)
        response = client.get(self.list_url)
        data = response.data.get('results')
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertEquals(
            len(data), 1,
            "Expected results mismatch (%s!=%s): %s"
            % (len(data), 1, response.data))
        first_result = data[0]
        self.assertIn('instance', first_result)
        self.assertIn('playbook_arguments', first_result)
        self.assertIn('playbook_name', first_result)
        self.assertIn('status', first_result)


class InstancePlaybookHistoryTests(APITestCase):
    def setUp(self):
        common_setup(self)
        self.list_view = InstancePlaybookHistoryViewSet.as_view({'get': 'list'})
        self.url_route = 'api:v2:instance_playbook_history'
        self.list_url = reverse(self.url_route+"-list")

    def test_valid_list(self):
        client = APIClient()

        client.force_authenticate(user=self.user_1)
        response = client.get(self.list_url)
        data = response.data.get('results')
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertEquals(
            len(data), 3,
            "Expected results mismatch (%s!=%s): %s"
            % (len(data), 3, response.data))
        first_result = data[0]
        self.assertIn('instance', first_result)
        self.assertIn('arguments', first_result)
        self.assertIn('status', first_result)
        self.assertIn('message', first_result)
        self.assertIn('timestamp', first_result)

        client.force_authenticate(user=self.user_2)
        response = client.get(self.list_url)
        data = response.data.get('results')
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertEquals(
            len(data), 1,
            "Expected results mismatch (%s!=%s): %s"
            % (len(data), 1, response.data))

    def test_valid_retrieve(self):
        client = APIClient()

        client.force_authenticate(user=self.user_1)
        response = client.get(self.list_url+"?instance_id=%s" % self.instance_1.provider_alias)
        data = response.data.get('results')
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertEquals(
            len(data), 3,
            "Expected results mismatch (%s!=%s): %s"
            % (len(data), 3, response.data))
        first_result = data[0]
        self.assertIn('instance', first_result)
        self.assertIn('arguments', first_result)
        self.assertIn('status', first_result)
        self.assertIn('message', first_result)
        self.assertIn('timestamp', first_result)

        client.force_authenticate(user=self.user_2)
        response = client.get(self.list_url+"?instance_id=%s" % self.instance_2.provider_alias)
        data = response.data.get('results')
        self.assertEquals(
            response.status_code, 200,
            "Expected 200, Received (%s):%s"
            % (response.status_code, response.data))
        self.assertEquals(
            len(data), 1,
            "Expected results mismatch (%s!=%s): %s"
            % (len(data), 1, response.data))
