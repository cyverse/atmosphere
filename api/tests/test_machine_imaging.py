from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest

import os

from datetime import datetime
from rest_framework import status
from threepio import logger
from urlparse import urljoin

from atmosphere import settings
from core.models import AtmosphereUser
from core.tests import create_euca_provider, create_os_provider
from api.tests import verify_expected_output, standup_instance
from api.tests.test_auth import TokenAPIClient
from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts
from django.test.utils import override_settings

class MachineRequestTests(TestCase):
    api_client = None
    expected_output = {
        "description": "", 
        "id": "", 
        "instance": "", 
        "name": "",
        "new_machine": "",
        "owner": "",
        "provider": "", 
        "shared_with": "", 
        "software": "", 
        "status": "", 
        "sys": "", 
        "tags": "", 
        "vis": ""
    }

    def setUp(self):
        #Initialize core DB
        self.euca_admin_id = create_euca_provider()
        self.euca_provider = self.euca_admin_id.provider
        self.os_admin_id = create_os_provider()
        self.os_provider = self.os_admin_id.provider
        #Ensure there is an account created/ready to go
        euca_accounts = EucaAccounts(self.euca_provider)
        euca_user = euca_accounts.get_user(settings.TEST_RUNNER_USER)
        self.euca_id = euca_accounts.create_account(euca_user, max_quota=True)
        os_accounts = OSAccounts(self.os_provider)
        self.os_id = os_accounts.create_account(
                settings.TEST_RUNNER_USER, 
                os_accounts.hashpass(settings.TEST_RUNNER_USER), max_quota=True)
        user = AtmosphereUser.objects.get(username=settings.TEST_RUNNER_USER)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        #Initialize API
        self.api_client = TokenAPIClient()
        self.api_client.login(
                username=settings.TEST_RUNNER_USER,
                password=settings.TEST_RUNNER_PASS)
        reverse_link = reverse('instance-list',
                               args=[self.os_id.provider.id,
                                     self.os_id.id])
        self.os_instance_url = urljoin(settings.SERVER_URL, reverse_link)
        reverse_link = reverse('instance-list',
                              args=[self.euca_id.provider.id,
                                    self.euca_id.id])
        self.euca_instance_url = urljoin(settings.SERVER_URL, reverse_link)
        reverse_link = reverse('machine-request-list',
                               args=[self.os_id.provider.id,
                                     self.os_id.id])
        self.os_request_url = urljoin(settings.SERVER_URL, reverse_link)
        reverse_link = reverse('machine-request-list',
                              args=[self.euca_id.provider.id,
                                    self.euca_id.id])
        self.euca_request_url = urljoin(settings.SERVER_URL, reverse_link)
        

    def tearDown(self):
        self.api_client.logout()

    #TEST CASES:
    def test_euca_machine_request(self):
        """
        Testing machine requests require specific order:
          * "Stand-up" an instance
          * Create a machine request
          * Approve a machine request
          * Verify machine request has gone to 'completed'
          * "Stand-up" the new machine
          * Delete an existing machine request
        """
        machine_alias = "emi-E7F8300F"
        size_alias = "m1.small"
        instance_id, instance_ip = standup_instance(
                self, self.euca_instance_url,
                machine_alias, size_alias, "test imaging")
        request_id = self.create_machine_request(
                self.euca_request_url,
                instance_id, instance_ip, self.euca_id.provider.id)
        approval_link = reverse('direct-machine-request-action',
                              args=[request_id, 'approve'])
        euca_approval_url = urljoin(settings.SERVER_URL, approval_link)
        self.approve_machine_request(euca_approval_url)
        machine_request_url = reverse('direct-machine-request-detail',
                args=[request_id,])
        new_machine_id = self.wait_for_machine_request(machine_request_url)
        machine_alias = new_machine_id
        instance_id, instance_ip = standup_instance(
                self, self.euca_instance_url,
                machine_alias, size_alias, "test imaging was successful",
                delete_after=True)

    def test_openstack_machine_request(self):
        """
        Testing machines must be done in order
          * Create a machine request
          * Approve a machine request
          * Verify a completed machine request
          * Delete a machine request
        # to verify a completed image:
        # Launch and Ensure: SSH, VNC, Shellinabox, Deploy access
        """
        machine_alias = "75fdfca4-d49d-4b2d-b919-a3297bc6d7ae"
        size_alias = "2"
        instance_id, instance_ip = standup_instance(
                self, self.os_instance_url,
                machine_alias, size_alias, "test imaging")
        request_id = self.create_machine_request(
                self.os_request_url,
                instance_id, instance_ip, self.os_id.provider.id)
        #E-mail for approval sent to ADMINS here..
        #Image ready for approval after this line returns
        approval_link = reverse('direct-machine-request-action',
                              args=[request_id, 'approve'])
        os_approval_url = urljoin(settings.SERVER_URL, approval_link)
        self.approve_machine_request(os_approval_url)
        #Machine will be imaged HERE.. Image EXISTS after this line returns!
        machine_request_url = reverse('direct-machine-request-detail',
                args=[request_id,])
        new_machine_id = self.wait_for_machine_request(machine_request_url)
        machine_alias = new_machine_id
        instance_id, instance_ip = standup_instance(
                self, self.os_instance_url,
                machine_alias, size_alias, "test imaging was successful",
                delete_after=True)

    #TEST STEPS: Called indirectly by TEST CASES...

    def create_machine_request(self, machine_request_url,
                               instance_id, instance_ip, new_provider_id):
        post_data = {
            "name":"Testing Machine Request",
            "description":"This is only a test, "\
                          "as such it is not meant to be launched.",
            "instance": instance_id,
            "provider": new_provider_id,
            "vis":"public",
            "ip_address":instance_ip,
            "software":"",
            "sys":"",
            "exclude":"",
            "tags":"",
        }
        post_machine_resp = self.api_client.post(machine_request_url,
                                                 post_data, format='json')
        #Validate the output
        self.assertEqual(post_machine_resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(post_machine_resp.data)
        #TODO:
        # Create 'expected output'
        # verify_expected_output(self, instance_launch_resp.data, self.expected_output)
        request_id = post_machine_resp.data['id']
        return request_id

    def approve_machine_request(self, machine_request_approval_url):
        mach_request_put = self.api_client.get(machine_request_approval_url)
        self.assertEqual(mach_request_put.status_code, status.HTTP_200_OK)

    def wait_for_machine_request(self, machine_request_url):
        finished = False
        minutes = 1
        attempts = 1
        while not finished:
            mach_request_get = self.api_client.get(machine_request_url)
            self.assertEqual(mach_request_get.status_code, status.HTTP_200_OK)
            mach_status = mach_request_get.data['status']
            new_machine = mach_request_get.data['new_machine']
            if 'error' in mach_status:
                raise Exception("Error occurred during imaging. "
                                "Will not wait for machine request to finish.")
                break
            if mach_status != 'completed':
                #5m, 5m, 5m, 5m, 5m, ...
                attempts += 1
                minutes = 5
                test_client.assertNotEqual(attempts, 10,
                    "Made 10 attempts to wait for an active instance. "
                    "Giving up..")
                continue
            finished = True
        complete_time = datetime.now()
        logger.info("Machine Request marked as completed. complete time:%s"
                    % (complete_time))
        return new_machine


if __name__ == "__main__":
   unittest.main()

