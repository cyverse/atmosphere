from django.test import TestCase
import mock

from api.tests.factories import (BootScriptRawTextFactory, InstanceFactory,
                                 UserFactory, AllocationSourceFactory,
                                 InstanceHistoryFactory)
from service.tasks.driver import deploy
from service.driver import get_esh_driver
from core.models import (InstanceAllocationSourceSnapshot,
                         UserAllocationSnapshot, AllocationSourceSnapshot,
                         UserAllocationSource)
from service.instance import _to_network_driver


class UserDeployTests(TestCase):
    def test_image_and_instance_scripts_are_included(self):
        user = UserFactory.create()
        instance = InstanceFactory.create(created_by=user)

        # Create/add instance script
        instance_script = BootScriptRawTextFactory.create(
            created_by=user, wait_for_deploy=True)
        instance.scripts.add(instance_script)

        # Create/add image script
        image_script = BootScriptRawTextFactory.create(
            created_by=user, wait_for_deploy=True)
        application_version = instance.source.providermachine.application_version
        application_version.boot_scripts.add(image_script)

        # Mock out ansible_deployment to verify its called with both image and
        # instance scripts
        with mock.patch(
                'service.deploy.ansible_deployment') as ansible_deployment:
            from service.deploy import user_deploy
            user_deploy(instance.ip_address, user.username,
                        instance.provider_alias)
            kwargs = ansible_deployment.call_args[1]
            script_titles = {
                s['name']
                for s in kwargs['extra_vars']['DEPLOY_SCRIPTS']
            }
            self.assertIn(instance_script.get_title_slug(), script_titles)
            self.assertIn(image_script.get_title_slug(), script_titles)


class DeployTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.instance = instance = InstanceFactory.create(created_by=self.user)
        InstanceHistoryFactory.create(instance=instance, status_name="active")
        self.mock_driver = get_esh_driver(instance.created_by_identity)
        self.mock_instance = self.mock_driver.create_instance(
            id=str(instance.provider_alias),
            ip=instance.ip_address,
            name=instance.name)
        network_driver = _to_network_driver(instance.created_by_identity)
        network_driver.create_port(
            None, None,
                device_id=str(instance.provider_alias),
                device_owner="compute:" + self.mock_instance.extra["availability_zone"]
            )
        network_driver.create_network(None, "test-network")
        network_driver.create_router(None, "test-router")
        identity = self.instance.created_by_identity
        cred = identity.credential_set.update_or_create(key="router_name", value="test-router")

        allocation = AllocationSourceFactory.create()
        UserAllocationSource.objects.create(
            allocation_source=allocation, user=self.user)
        UserAllocationSnapshot.objects.create(
            allocation_source=allocation,
            user=self.user,
            burn_rate=1,
            compute_used=0)
        AllocationSourceSnapshot.objects.create(
            allocation_source=allocation,
            compute_used=0,
            compute_allowed=168,
            global_burn_rate=1)
        InstanceAllocationSourceSnapshot.objects.update_or_create(
            instance=instance, allocation_source=allocation)

    def test_instance_success_email(self):
        """
        Assert that the instance email is only sent on the first deploy
        """
        driver = self.mock_driver
        instance_id = self.mock_instance.id
        core_identity_uuid = self.instance.created_by_identity.uuid
        username = self.user.username
        with mock.patch('service.deploy.ansible_deployment'), \
            mock.patch('service.tasks.driver.send_instance_email') as mocked_send_email:
            deploy(driver.__class__, driver.provider, driver.identity, instance_id,
                   core_identity_uuid, username)
            mocked_send_email.assert_called_once()
            mocked_send_email.reset_mock()
            deploy(driver.__class__, driver.provider, driver.identity, instance_id,
                   core_identity_uuid, username)
            mocked_send_email.assert_not_called()

    # def test_deploy_failure(self):
    #     driver = self.mock_driver
    #     instance_id = self.mock_instance.id
    #     core_identity_uuid = self.instance.created_by_identity.uuid
    #     username = self.user.username
    #     with mock.patch('service.deploy.ansible_deployment'), \
    #         mock.patch('service.tasks.driver.add_fixed_ip.run') as mocked_add_fixed:
    #         mocked_add_fixed.side_effect = Exception("An unknown error occurred")
    #         deploy(driver.__class__, driver.provider, driver.identity, instance_id,
    #                core_identity_uuid, username)
    #         # print mocked_add_fixed.call_count
    #         pass
