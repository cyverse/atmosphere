import uuid
from unittest import skip, skipIf
from django.test import override_settings, TestCase
from django.core.urlresolvers import reverse
from django.utils import timezone
import mock
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory, force_authenticate

from api.tests.factories import (
    UserFactory, AnonymousUserFactory, InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ApplicationVersionFactory, ProviderMachineFactory, IdentityFactory, ProviderFactory,
    SizeFactory, AllocationSourceFactory)
from api.v2.views import InstanceViewSet
from core.models import (
    InstanceStatusHistory,
    InstanceAllocationSourceSnapshot,
    UserAllocationSnapshot, AllocationSourceSnapshot,
    UserAllocationSource)
from service.driver import get_esh_driver


class InstanceActionTests(TestCase):

    def setUp(self):
        self.user = UserFactory.create()
        self.instance = instance = InstanceFactory.create(created_by=self.user)
        mock_driver = get_esh_driver(instance.created_by_identity)
        self.mock_instance = mock_driver.create_instance(
            id=str(instance.provider_alias),
            ip=instance.ip_address,
            name=instance.name)
        allocation = AllocationSourceFactory.create(name='test_allocation')
        UserAllocationSource.objects.create(
                allocation_source=allocation,
                user=self.user)
        UserAllocationSnapshot.objects.create(
                allocation_source=allocation,
                user=self.user,
                burn_rate=1,
                compute_used=0)
        AllocationSourceSnapshot.objects.create(
            allocation_source=allocation,
            compute_used=0,
            compute_allowed=168,
            global_burn_rate=1
        )
        InstanceAllocationSourceSnapshot.objects.update_or_create(instance=instance,
                                                                  allocation_source=allocation)

        self.url = "{base_url}/{instance_alias}/actions".format(
            base_url=reverse('api:v2:instance-list'),
            instance_alias=self.instance.provider_alias)
        self.view = InstanceViewSet.as_view({'post': 'actions'})

    def test_start_instance(self):
        current_status = "shutoff"
        new_status = "active"
        action = "start"
        InstanceHistoryFactory.create(instance=self.instance, status_name=current_status)
        self.mock_instance.extra['status'] = new_status

        current_history = InstanceStatusHistory.latest_history(self.instance)
        response = self._perform_action({ 'action': action })
        next_history = InstanceStatusHistory.latest_history(self.instance)

        self.assertEquals(response.status_code, 200)
        self.assertNotEquals(current_history, next_history)

    def test_stop_instance(self):
        current_status = "active"
        new_status = "shutoff"
        action = "stop"
        InstanceHistoryFactory.create(instance=self.instance, status_name=current_status)
        self.mock_instance.extra['status'] = new_status

        current_history = InstanceStatusHistory.latest_history(self.instance)
        response = self._perform_action({ 'action': action })
        next_history = InstanceStatusHistory.latest_history(self.instance)

        self.assertEquals(response.status_code, 200)
        self.assertNotEquals(current_history, next_history)

    def test_redeploy_instance(self):
        current_status = "active"
        new_status = "active"
        action = "redeploy"
        InstanceHistoryFactory.create(instance=self.instance, status_name=current_status)
        self.mock_instance.extra['status'] = new_status

        current_history = InstanceStatusHistory.latest_history(self.instance)
        response = self._perform_action({ 'action': action })
        next_history = InstanceStatusHistory.latest_history(self.instance)

        self.assertEquals(response.status_code, 200)
        self.assertNotEquals(current_history, next_history)

    def test_resume_instance(self):
        current_status = "suspended"
        new_status = "active"
        action = "resume"
        InstanceHistoryFactory.create(instance=self.instance, status_name=current_status)
        self.mock_instance.extra['status'] = new_status

        current_history = InstanceStatusHistory.latest_history(self.instance)
        response = self._perform_action({ 'action': action })
        next_history = InstanceStatusHistory.latest_history(self.instance)

        self.assertEquals(response.status_code, 200)
        self.assertNotEquals(current_history, next_history)

    def test_suspend_instance(self):
        current_status = "active"
        new_status = "suspended"
        action = "suspend"
        InstanceHistoryFactory.create(instance=self.instance, status_name=current_status)
        self.mock_instance.extra['status'] = new_status

        current_history = InstanceStatusHistory.latest_history(self.instance)
        response = self._perform_action({ 'action': action })
        next_history = InstanceStatusHistory.latest_history(self.instance)

        self.assertEquals(response.status_code, 200)
        self.assertNotEquals(current_history, next_history)

    def test_reboot_instance(self):
        current_status = "active"
        new_status = "active"
        new_task = "powering-on"
        action = "reboot"
        InstanceHistoryFactory.create(instance=self.instance, status_name=current_status)
        self.mock_instance.extra['status'] = new_status
        self.mock_instance.extra['task'] = new_task

        current_history = InstanceStatusHistory.latest_history(self.instance)
        response = self._perform_action({ 'action': action, 'reboot_type': 'SOFT' })
        next_history = InstanceStatusHistory.latest_history(self.instance)

        self.assertEquals(response.status_code, 200)
        self.assertNotEquals(current_history, next_history)

    @override_settings(ALLOCATION_OVERRIDES_ALWAYS_ENFORCE=['test_allocation'])
    def test_start_instance_when_allocation_blacklisted(self):
        factory = APIRequestFactory()
        request = factory.post(self.url, { 'action': 'start' })
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.instance.provider_alias))

        # Check the status code
        self.assertEquals(response.status_code, 403);

        # Check the error message
        target_error_message = "Allocation 'test_allocation' has been blacklisted by staff"
        error_messages = [ e['message'] for e in response.data['errors'] ]
        target_error_was_included = any(target_error_message in message for message in error_messages)
        self.assertTrue(target_error_was_included)

    def _perform_action(self, data):
        factory = APIRequestFactory()
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)

        # Patch celery async calls (deployment and cloud polling) because
        # we want to test/ensure that the instance status changes synchronously
        # in the same request
        with mock.patch('service.tasks.driver.deploy.run'), \
            mock.patch('service.tasks.driver.wait_for_instance.run'):
            response = self.view(request, str(self.instance.provider_alias))
            return response
