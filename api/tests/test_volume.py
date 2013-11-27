from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest

import os
import time

from rest_framework import status
from threepio import logger
from urlparse import urljoin

from atmosphere import settings
from core.tests import create_euca_provider, create_os_provider
from api.tests import verify_expected_output
from api.tests.test_auth import TokenAPIClient
from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts

class VolumeTests(TestCase):
    client = None
    expected_output = {
            "status": "", 
            "attach_data": "", 
            "alias": "", 
            "provider": "",
            "size": "",
            "name": "",
            "description": "", 
            "created_by": "",
            "created_by_identity": "",
            "start_date": ""
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
        self.euca_id = euca_accounts.create_account(euca_user)
        os_accounts = OSAccounts(self.os_provider)
        self.os_id = os_accounts.create_account(
                settings.TEST_RUNNER_USER, 
                os_accounts.hashpass(settings.TEST_RUNNER_USER))
        #Initialize API
        self.client = TokenAPIClient()
        self.client.login(
                username=settings.TEST_RUNNER_USER,
                password=settings.TEST_RUNNER_PASS)
        reverse_link = reverse('volume-list',
                               args=[self.os_id.provider.id,
                                     self.os_id.id])
        self.os_volume_url = urljoin(settings.SERVER_URL, reverse_link)
        reverse_link = reverse('volume-list',
                              args=[self.euca_id.provider.id,
                                    self.euca_id.id])
        self.euca_volume_url = urljoin(settings.SERVER_URL, reverse_link)
        

    def tearDown(self):
        self.client.logout()

    def test_euca_volume(self):
        """
        Testing volumes must be done in order
        * Create the volume
        * Detail the volume
        * Delete the volume
        # Wait for volume to deploy and
        # Ensure: SSH, VNC, Shellinabox, Deploy access
        """

        euca_launch_data = {
            "name":"euca_vol_test1",
            "size":1,
        }
        self.expected_output['name'] = euca_launch_data['name']
        self.expected_output['size'] = euca_launch_data['size']
        deleted = self.predelete_step_euca()
        if deleted:
            # Give it some time to clear, so we dont go over-quota..
            time.sleep(30) # Sorry, its euca.

        volume_id = self.launch_step_euca(euca_launch_data)
        self.detail_step_euca(volume_id)
        #self.delete_step_euca(volume_id)

    def launch_step_euca(self, euca_launch_data):
        #Create the volume
        volume_launch_resp = self.client.post(self.euca_volume_url, euca_launch_data, format='json')
        #Validate the output
        self.assertEqual(volume_launch_resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(volume_launch_resp.data)
        verify_expected_output(self, volume_launch_resp.data, self.expected_output)
        volume_id = volume_launch_resp.data['alias']
        return volume_id

    def predelete_step_euca(self):
        list_volume_resp = self.client.get(self.euca_volume_url)
        self.assertEqual(list_volume_resp.status_code, status.HTTP_200_OK)
        if not list_volume_resp.data:
            return False
        for volume in list_volume_resp.data:
            self.delete_step_euca(volume['alias'])
        return True

    def detail_step_euca(self, volume_id):
        #Detail the volume
        new_euca_volume_url = urljoin(
                self.euca_volume_url,
                '%s/' % volume_id)
        logger.info("Testing on url:%s" % new_euca_volume_url)
        volume_get_resp = self.client.get(new_euca_volume_url)
        logger.info("URL Response: %s" % volume_get_resp)
        #Validate the output
        self.assertEqual(volume_get_resp.status_code, status.HTTP_200_OK)
        verify_expected_output(self, volume_get_resp.data, self.expected_output)

    def delete_step_euca(self, volume_id):
        new_euca_volume_url = urljoin(
                self.euca_volume_url,
                '%s/' % volume_id)
        logger.info("Testing on url:%s" % new_euca_volume_url)
        #Delete the volume
        delete_resp = self.client.delete(new_euca_volume_url)
        #Validate the output
        self.assertEqual(delete_resp.status_code, status.HTTP_200_OK)

    def test_openstack_volume(self):
        """
        Testing volumes must be done in order
        * Create the volume
        * Detail the volume
        * Delete the volume
        """
        os_launch_data = {
            "name":"openstack_vol_test1",
            "size":1,
        }
        self.expected_output['name'] = os_launch_data['name']
        self.expected_output['size'] = os_launch_data['size']
        deleted = self.predelete_step_os()
        if deleted:
            # Give it some time to clear, so we dont go over-quota..
            time.sleep(30)
        volume_id = self.launch_step_os(os_launch_data)
        self.detail_step_os(volume_id)
        #self.delete_step_os(volume_id)

    def launch_step_os(self, os_launch_data):
        #Create the volume
        volume_launch_resp = self.client.post(self.os_volume_url, os_launch_data, format='json')
        #Validate the output
        self.assertEqual(volume_launch_resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(volume_launch_resp.data)
        verify_expected_output(self, volume_launch_resp.data, self.expected_output)
        return volume_launch_resp.data['alias']

    def detail_step_os(self, volume_id):
        #Detail the volume
        new_os_volume_url = urljoin(
                self.os_volume_url,
                '%s/' % volume_id)
        volume_get_resp = self.client.get(new_os_volume_url)
        #Validate the output
        self.assertEqual(volume_get_resp.status_code, status.HTTP_200_OK)
        verify_expected_output(self, volume_get_resp.data, self.expected_output)

    def predelete_step_os(self):
        list_volume_resp = self.client.get(self.os_volume_url)
        self.assertEqual(list_volume_resp.status_code, status.HTTP_200_OK)
        if not list_volume_resp.data:
            return False
        for volume in list_volume_resp.data:
            self.delete_step_os(volume['alias'])
        return True
        
    def delete_step_os(self, volume_id):
        new_os_volume_url = urljoin(self.os_volume_url, '%s/' % volume_id)
        #Delete the volume
        delete_resp = self.client.delete(new_os_volume_url)
        #Validate the output
        self.assertEqual(delete_resp.status_code, status.HTTP_200_OK)


if __name__ == "__main__":
   unittest.main()

