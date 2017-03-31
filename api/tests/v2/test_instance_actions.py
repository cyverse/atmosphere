import uuid
from unittest import skip, skipIf

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.tests.factories import (
    GroupFactory, UserFactory, AnonymousUserFactory, InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ImageFactory, ApplicationVersionFactory, InstanceSourceFactory, ProviderMachineFactory, IdentityFactory, ProviderFactory,
    IdentityMembershipFactory, QuotaFactory)
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

        self.view = InstanceViewSet.as_view({'post': 'actions'})
        factory = APIRequestFactory()
        self.url = reverse('api:v2:instance-list')
        self.url += "/" + str(self.active_instance.provider_alias) + "/actions"
        data = {
            'action': 'stop'
        }
        self.request = factory.post(self.url, data)
        self.mock_driver = get_esh_driver(self.user_identity)
        self.mock_driver.add_core_instance(self.active_instance)

    # For resize, I will add a size in InstanceStatusHistory. for stop, we don't have to have
    def test_stop_instance_action(self):
        force_authenticate(self.request, user=self.user)
        response = self.view(self.request, str(self.active_instance.provider_alias))
        data = response.data.get('results')
        if data:
            result = data[0]
        self.assertEquals(response.status_code, 200)
