from django.test import TestCase
import mock

from api.tests.factories import BootScriptRawTextFactory, InstanceFactory, UserFactory


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
