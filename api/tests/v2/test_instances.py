import uuid
from unittest import skip, skipIf
import mock

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.tests.factories import (
    GroupFactory, UserFactory, AnonymousUserFactory, InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory, SizeFactory,
    ImageFactory, ApplicationVersionFactory, InstanceSourceFactory, ProviderMachineFactory, IdentityFactory, ProviderFactory,
    IdentityMembershipFactory, QuotaFactory)
from .base import APISanityTestCase
from api.v2.views import InstanceViewSet
from core.models import AtmosphereUser


class InstanceTests(APITestCase, APISanityTestCase):
    url_route = 'api:v2:instance'

    def setUp(self):
        self.list_view = InstanceViewSet.as_view({'get': 'list'})
        self.detailed_view = InstanceViewSet.as_view({'get': 'retrieve'})
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create(username='test-username')
        self.admin_user = UserFactory.create(username='admin', is_superuser=True, is_staff=True)
        self.provider = ProviderFactory.create()
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user,
            provider=self.provider)
        self.admin_identity = IdentityFactory.create_identity(
            provider=self.provider,
            created_by=self.admin_user)

        self.machine = ProviderMachineFactory.create_provider_machine(self.user, self.user_identity)
        self.active_instance = InstanceFactory.create(
            name="Instance in active",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=timezone.now())
        self.networking_instance = InstanceFactory.create(
            name="Instance in networking",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=timezone.now())
        self.deploying_instance = InstanceFactory.create(
            name="Instance in deploying",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=timezone.now())
        self.deploy_error_instance = InstanceFactory.create(
            name="Instance in deploy_error",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=timezone.now())

        active = InstanceStatusFactory.create(name='active')
        networking = InstanceStatusFactory.create(name='networking')
        deploying = InstanceStatusFactory.create(name='deploying')
        deploy_error = InstanceStatusFactory.create(name='deploy_error')

        InstanceHistoryFactory.create(
                status=deploy_error,
                activity="",
                instance=self.deploy_error_instance
            )
        InstanceHistoryFactory.create(
                status=deploying,
                activity="",
                instance=self.deploying_instance
            )
        InstanceHistoryFactory.create(
                status=active,
                activity="",
                instance=self.active_instance
            )
        InstanceHistoryFactory.create(
                status=networking,
                activity="",
                instance=self.networking_instance
            )

    def test_networking_status_and_activity(self):
        """Will only work with a correct database."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        url = reverse(self.url_route+"-detail", args=(self.networking_instance.provider_alias,))
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        data = response.data
        self.assertEquals(data['status'], 'active')
        self.assertEquals(data['activity'], 'networking')

    def test_deploying_status_and_activity(self):
        """Will only work with a correct database."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        url = reverse(self.url_route+"-detail", args=(self.deploying_instance.provider_alias,))
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        data = response.data
        self.assertEquals(data['status'], 'active')
        self.assertEquals(data['activity'], 'deploying')

    def test_deploy_error_status_and_activity(self):
        """Will only work with a correct database."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        url = reverse(self.url_route+"-detail", args=(self.deploy_error_instance.provider_alias,))
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        data = response.data
        self.assertEquals(data['status'], 'active')
        self.assertEquals(data['activity'], 'deploy_error')

    def test_active_status_and_activity(self):
        """Will only work with a correct database."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        url = reverse(self.url_route+"-detail", args=(self.active_instance.provider_alias,))
        response = client.get(url)
        self.assertEquals(response.status_code, 200, "Non-200 response returned: (%s) %s" % (response.status_code, response.data))
        data = response.data
        self.assertEquals(data['status'], 'active')
        self.assertEquals(data['activity'], '')

    def test_instance_delete(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        url = reverse(self.url_route+"-detail", args=(self.active_instance.provider_alias,))
        with mock.patch('api.v2.views.instance.destroy_instance'):
            response = client.delete(url, HTTP_ACCEPT='application/json')
        self.assertEquals(response.status_code, 204)
