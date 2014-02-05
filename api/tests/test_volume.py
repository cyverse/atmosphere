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
from api.tests import verify_expected_output, standup_instance
from api.tests.test_auth import TokenAPIClient
from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts

class VolumeTests(TestCase):
    api_client = None
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
        self.euca_id = euca_accounts.create_account(euca_user, max_quota=True)
        os_accounts = OSAccounts(self.os_provider)
        self.os_id = os_accounts.create_account(
                settings.TEST_RUNNER_USER, 
                os_accounts.hashpass(settings.TEST_RUNNER_USER), max_quota=True)
        #user = AtmosphereUser.objects.get(username=settings.TEST_RUNNER_USER)
        #user.is_staff = True
        #user.is_superuser = True
        #user.save()
        #Initialize API
        self.api_client = TokenAPIClient()
        self.api_client.login(
                username=settings.TEST_RUNNER_USER,
                password=settings.TEST_RUNNER_PASS)
        reverse_link = reverse('instance-list',
                              args=[self.os_id.provider.id,
                                    self.os_id.id])
        self.os_instance_url = urljoin(settings.SERVER_URL, reverse_link)
        reverse_link = reverse('volume-list',
                               args=[self.os_id.provider.id,
                                     self.os_id.id])
        #Prepare Openstack
        self.os_volume_url = urljoin(settings.SERVER_URL, reverse_link)
        instance_data = {
                "size_alias":"2",
                "machine_alias":"0f539197-3718-40bc-8a29-c22e0841684f",
                "name":"test volume attachment",
                "delete_before":False
            }
        (self.os_instance_id, self.os_instance_ip) = standup_instance(
                self, self.os_instance_url, **instance_data)

        #Prepare Eucalyptus
        reverse_link = reverse('volume-list',
                              args=[self.euca_id.provider.id,
                                    self.euca_id.id])
        self.euca_volume_url = urljoin(settings.SERVER_URL, reverse_link)
        reverse_link = reverse('instance-list',
                              args=[self.euca_id.provider.id,
                                    self.euca_id.id])
        self.euca_instance_url = urljoin(settings.SERVER_URL, reverse_link)
        instance_data = {
                "size_alias":"m1.small",
                "machine_alias":"emi-E7F8300F",
                "name":"test volume attachment",
                "delete_before":False
            }
        (self.euca_instance_id, self.euca_instance_ip) = standup_instance(
                self, self.euca_instance_url, **instance_data)
        

    def tearDown(self):
        self.api_client.logout()

    def test_openstack_volume(self):
        """
        Testing volumes must be done in order
        * Create the volume
        * Detail the volume
        * Delete the volume
        """
        volume_post_data = {
            "name":"openstack_vol_test1",
            "size":1,
        }
        self.expected_output['name'] = volume_post_data['name']
        self.expected_output['size'] = volume_post_data['size']
        volume_id = self.create_volume(self.os_volume_url, volume_post_data)
        self.detail_volume(self.os_volume_url, volume_id)
        # Wait time associated between 'create' and 'attachment'
        time.sleep(30)
        self.attach_volume(self.os_instance_url, self.os_instance_id, volume_id)
        time.sleep(30)
        self.detach_volume(self.os_instance_url, self.os_instance_id, volume_id)
        # Wait time associated between 'detach' and 'delete'
        time.sleep(30) # Sorry, its euca.
        #Delete all volumes
        deleted = self.delete_all_volumes(self.os_volume_url)


    #def test_euca_volume(self):
    #    """
    #    Testing volumes must be done in order
    #    * Create the volume
    #    * wait a second
    #    * Attach the volume
    #    * Verify success
    #    * If failed, Try again(?)
    #    * Detach the volume
    #    * Verify success
    #    * wait a second
    #    * Delete the volume
    #    # Wait for volume to deploy and
    #    # Ensure: SSH, VNC, Shellinabox, Deploy access
    #    """

    #    volume_post_data = {
    #        "name":"euca_vol_test1",
    #        "size":1,
    #    }
    #    self.expected_output['name'] = volume_post_data['name']
    #    self.expected_output['size'] = volume_post_data['size']

    #    volume_id = self.create_volume(self.euca_volume_url, volume_post_data)
    #    self.detail_volume(self.euca_volume_url, volume_id)
    #    # Wait time associated between 'create' and 'attachment'
    #    time.sleep(30)
    #    self.attach_volume(self.euca_instance_url, self.euca_instance_id, volume_id)
    #    time.sleep(30)
    #    self.detach_volume(self.euca_instance_url, self.euca_instance_id, volume_id)
    #    #Delete all volumes
    #    deleted = self.delete_all_volumes(self.euca_volume_url)
    #    if deleted:
    #        # Wait time associated between 'detach' and 'delete'
    #        time.sleep(30) # Sorry, its euca.

    def attach_volume(self, instance_base_url, instance_id, volume_id):
        #Make action url
        instance_action_url = urljoin(
            urljoin(instance_base_url, '%s/' % instance_id),
            'action/')
        #Attach volume parameters
        action_params = {
            'action':'attach_volume',
            'volume_id':volume_id,
            #'device':'/dev/xvdb',
        }
        volume_attach_resp = self.api_client.post(instance_action_url,
                                                  action_params, format='json')
        #Wait and see..

    def detach_volume(self, instance_base_url, instance_id, volume_id):
        #Make action url
        instance_action_url = urljoin(
            urljoin(instance_base_url, '%s/' % instance_id), 'action/')
        #Attach volume parameters
        action_params = {
            'action': 'detach_volume',
            'volume_id': volume_id,
            #'device': '/dev/xvdb',
        }
        volume_detach_resp = self.api_client.post(instance_action_url,
                                                  action_params, format='json')
        #Wait and see..

    def create_volume(self, volume_base_url, post_data):
        #Create the volume
        volume_launch_resp = self.api_client.post(volume_base_url, post_data,
                                                  format='json')
        #Validate the output
        if volume_launch_resp.status_code != status.HTTP_201_CREATED:
            logger.info(volume_launch_resp)
        self.assertEqual(volume_launch_resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(volume_launch_resp.data)
        verify_expected_output(self, volume_launch_resp.data,
                               self.expected_output)
        volume_id = volume_launch_resp.data['alias']
        return volume_id

    def delete_all_volumes(self, volume_list_url):
        list_volume_resp = self.api_client.get(volume_list_url)
        self.assertEqual(list_volume_resp.status_code, status.HTTP_200_OK)
        if not list_volume_resp.data:
            return False
        for volume in list_volume_resp.data:
            self.delete_volume(volume_list_url, volume['alias'])
        return True

    def delete_volume(self, volume_base_url, volume_alias):
        specific_volume_url = urljoin(
            volume_base_url,
            '%s/' % volume_alias)
        #Delete the volume
        delete_resp = self.api_client.delete(specific_volume_url)
        #Validate the output
        self.assertEqual(delete_resp.status_code, status.HTTP_200_OK)


    def detail_volume(self, volume_base_url, volume_id):
        #Detail the volume
        specific_volume_url = urljoin(
            volume_base_url,
            '%s/' % volume_id)
        volume_get_resp = self.api_client.get(specific_volume_url)
        #Validate the output
        self.assertEqual(volume_get_resp.status_code, status.HTTP_200_OK)
        verify_expected_output(self, volume_get_resp.data,
                               self.expected_output)


if __name__ == "__main__":
    unittest.main()
