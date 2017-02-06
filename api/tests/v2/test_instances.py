import json
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


class InstanceTests(APITestCase):
    def setUp(self):
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
        self.instance_1 = InstanceFactory.create(
            name="Instance 1",
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=timezone.now())
        active = InstanceStatusFactory.create(name='active')
        networking = InstanceStatusFactory.create(name='networking')
        deploying = InstanceStatusFactory.create(name='deploying')
        deploy_error = InstanceStatusFactory.create(name='deploy_error')
        history_1 = InstanceHistoryFactory.create(
                status=active,
                activity="",
                instance=self.instance_1
            )

    def test_a_sanity_check(self):
        """Will only work with a correct database."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        url = '/api/v2/instances'
        response = client.get(url)
        #FIXME: This fails here with: `ImproperlyConfigured: Could not resolve URL for hyperlinked relationship using view name "api:v2:instance-detail".`
        self.assertEquals(response.status_code, 200)

