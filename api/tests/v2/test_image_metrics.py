import uuid

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from rest_framework.test import APITestCase
from api.tests.factories import (
    UserFactory, AnonymousUserFactory, InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ProviderMachineFactory, IdentityFactory, ProviderFactory
)

from core.metrics import get_application_metrics


class InstanceTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create(username='test-username')
        self.provider = ProviderFactory.create()
        self.user_identity = IdentityFactory.create_identity(
            created_by=self.user,
            provider=self.provider)

        self.machine = ProviderMachineFactory.create_provider_machine(self.user, self.user_identity)
        self.application = self.machine.application_version.application
        start_date = timezone.now()
        self.active_instance = InstanceFactory.create(
            name="Instance went active",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=start_date)
        self.networking_instance = InstanceFactory.create(
            name="Instance stuck in networking",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=start_date)
        self.deploying_instance = InstanceFactory.create(
            name="Instance stuck in deploying",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=start_date)
        self.deploy_error_instance = InstanceFactory.create(
            name="Instance stuck in deploy_error",
            provider_alias=uuid.uuid4(),
            source=self.machine.instance_source,
            created_by=self.user,
            created_by_identity=self.user_identity,
            start_date=start_date)

        build = InstanceStatusFactory.create(name='build')
        active = InstanceStatusFactory.create(name='active')
        networking = InstanceStatusFactory.create(name='networking')
        deploying = InstanceStatusFactory.create(name='deploying')
        deploy_error = InstanceStatusFactory.create(name='deploy_error')
        # Adding two minutes to simulate the passage of time.
        delta_time = timezone.timedelta(minutes=2)
        # Simulate 'Deploy error'
        InstanceHistoryFactory.create(
                status=build,
                activity="",
                instance=self.deploy_error_instance,
                start_date=start_date,
            )
        InstanceHistoryFactory.create(
                status=networking,
                activity="",
                instance=self.deploy_error_instance,
                start_date=start_date + delta_time,
            )
        InstanceHistoryFactory.create(
                status=deploying,
                activity="",
                instance=self.deploy_error_instance,
                start_date=start_date + delta_time*2,
            )
        InstanceHistoryFactory.create(
                status=deploy_error,
                activity="",
                instance=self.deploy_error_instance,
                start_date=start_date + delta_time*3,
            )
        # Simulate 'stuck in networking'
        InstanceHistoryFactory.create(
                status=build,
                activity="",
                instance=self.networking_instance,
                start_date=start_date,
            )
        InstanceHistoryFactory.create(
                status=networking,
                activity="",
                instance=self.networking_instance,
                start_date=start_date + delta_time,
            )
        # Simulate 'stuck in deploying'
        InstanceHistoryFactory.create(
                status=build,
                activity="",
                instance=self.deploying_instance,
                start_date=start_date + delta_time,
            )
        InstanceHistoryFactory.create(
                status=networking,
                activity="",
                instance=self.deploying_instance,
                start_date=start_date + delta_time,
            )
        InstanceHistoryFactory.create(
                status=deploying,
                activity="",
                instance=self.deploying_instance,
                start_date=start_date + delta_time,
            )
        # Simulate going to active
        InstanceHistoryFactory.create(
                status=build,
                activity="",
                instance=self.active_instance,
                start_date=start_date,
            )
        InstanceHistoryFactory.create(
                status=networking,
                activity="",
                instance=self.active_instance,
                start_date=start_date + delta_time,
            )
        InstanceHistoryFactory.create(
                status=deploying,
                activity="",
                instance=self.active_instance,
                start_date=start_date + delta_time*2,
            )
        InstanceHistoryFactory.create(
                status=active,
                activity="",
                instance=self.active_instance,
                start_date=start_date + delta_time*3,
            )
        get_application_metrics(self.application)

    def test_accurate_application_statistics(self):
        """Given the setUp above, 1/4 instances are active."""
        client = APIClient()
        client.force_authenticate(user=self.user)
        expected_metrics = {'active': 1, 'total': 4}

        url = reverse('api:v2:applicationmetric-detail', args=(self.application.uuid,))
        response = client.get(url)
        self.assertEquals(response.status_code, 200)
        data = response.data
        api_metrics = data['metrics']
        metrics = api_metrics.values()[0]

        self.assertEquals(metrics, expected_metrics)
