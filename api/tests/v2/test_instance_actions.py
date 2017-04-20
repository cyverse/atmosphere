import uuid
from unittest import skip, skipIf

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.tests.factories import (
    UserFactory, AnonymousUserFactory, InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ApplicationVersionFactory, ProviderMachineFactory, IdentityFactory, ProviderFactory,
    SizeFactory)
from api.v2.views import InstanceViewSet
from core.models import AtmosphereUser
from rtwo.driver import MockDriver
from service.driver import get_esh_driver

class InstanceActionTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create(username='test-username')
        self.provider = ProviderFactory.create(type__name='mock')
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user,
            provider=self.provider)
        self.machine = ProviderMachineFactory.create_provider_machine(self.user, self.user_identity)
        start_date = timezone.now()
        self.active_instance = InstanceFactory.create(
            name="Instance in active",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=start_date)
        self.status_active = InstanceStatusFactory.create(name='active')
        delta_time = timezone.timedelta(minutes=2)
        InstanceHistoryFactory.create(
                status=self.status_active,
                activity="",
                instance=self.active_instance,
                start_date=start_date + delta_time*3)

        self.view = InstanceViewSet.as_view({
            'get': 'actions',
            'post': 'actions'
        })
        self.url = reverse('api:v2:instance-list')
        self.url += "/" + str(self.active_instance.provider_alias) + "/actions"
        self.mock_driver = get_esh_driver(self.user_identity)
        self.mock_driver.add_core_instance(self.active_instance)

        start_date_second = timezone.now()
        self.active_instance_second = InstanceFactory.create(
            name="Instance in active",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=start_date_second)
        self.status_active_second = InstanceStatusFactory.create(name='active')
        delta_time = timezone.timedelta(minutes=2)
        self.size_small = SizeFactory.create(provider=self.provider, cpu=2, disk=20, root=0, mem=128)
        self.size_large = SizeFactory.create(provider=self.provider, cpu=4, disk=40, root=0, mem=256)
        InstanceHistoryFactory.create(
                status=self.status_active_second,
                size=self.size_small,
                activity="",
                instance=self.active_instance_second,
                start_date=start_date_second + delta_time*3)
        self.mock_driver_second = get_esh_driver(self.user_identity)
        self.mock_driver.add_core_instance(self.active_instance_second)

    def test_get_instance_action_count_for_active_instance(self):
        factory = APIRequestFactory()
        request = factory.get(self.url)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        self.assertEquals(response.status_code, 200)
        actions = response.data
        self.assertEquals(len(actions), 8)
        for action_name in [
                "Stop", "Suspend",
                "Terminate", "Shelve",
                "Reboot", "Hard Reboot",
                "Resize", "Imaging"]:
            self.assertTrue(
                any(a for a in actions if action_name == a.get('key'))
            )

    # For resize, I will add a size in InstanceStatusHistory. for stop, we don't have to have
    def test_stop_instance_action(self):
        factory = APIRequestFactory()
        data = {
            'action': 'stop'
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        data = response.data.get('result')
        self.assertEquals(response.status_code, 200)
        self.assertEquals('success', data)

    def test_start_instance_action(self):
        factory = APIRequestFactory()
        data = {
            'action': 'start'
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        data = response.data.get('result')
        self.assertEquals(response.status_code, 200)
        self.assertEquals('success', data)

    def test_reboot_soft_instance_action(self):
        factory = APIRequestFactory()
        data = {
            'action': 'reboot',
            'reboot_type': 'SOFT'
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        self.assertEquals(response.status_code, 200)
        data = response.data.get('result')
        self.assertEquals('success', data)

    def test_reboot_hard_instance_action(self):
        factory = APIRequestFactory()
        data = {
            'action': 'reboot',
            'reboot_type': 'HARD'
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        self.assertEquals(response.status_code, 200)
        data = response.data.get('result')
        self.assertEquals('success', data)

    def test_suspend_instance_action(self):
        factory = APIRequestFactory()
        data = {
            'action': 'suspend'
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        self.assertEquals(response.status_code, 200)
        data = response.data.get('result')
        self.assertEquals('success', data)

    def test_resume_instance_action(self):
        factory = APIRequestFactory()
        data = {
            'action': 'resume'
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        self.assertEquals(response.status_code, 200)
        data = response.data.get('result')
        self.assertEquals('success', data)

    def test_redeploy_instance_action(self):
        factory = APIRequestFactory()
        data = {
            'action': 'redeploy'
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        self.assertEquals(response.status_code, 200)
        data = response.data.get('result')
        self.assertEquals('success', data)

    def test_resize_instance_action(self):
        factory = APIRequestFactory()
        data = {
            "action":"resize",
            "resize_size":self.size_large.alias
        }
        request = factory.post(self.url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request, str(self.active_instance.provider_alias))
        self.assertEquals(response.status_code, 200)
        data = response.data.get('result')
        self.assertEquals('success', data)
