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

delete_instances = False
os_base_instance_url = ""

#Special method run once per testcase
def setUpModule():
    setUp_openstack()
    setUp_euca()

def setUp_euca():
    euca_admin_id = create_euca_provider()
    euca_provider = euca_admin_id.provider
    #Ensure there is an account created/ready to go
    euca_accounts = EucaAccounts(euca_provider)
    euca_user = euca_accounts.get_user(settings.TEST_RUNNER_USER)
    euca_id = euca_accounts.create_account(euca_user, max_quota=True)
    reverse_link = reverse('instance-list',
                          args=[euca_id.provider.id,
                                euca_id.id])
    euca_instance_url = urljoin(settings.SERVER_URL, reverse_link)

def setUp_openstack():
    #Initialize core DB
    global os_base_instance_url
    os_admin_id = create_os_provider()
    os_provider = os_admin_id.provider
    os_accounts = OSAccounts(os_provider)
    os_id = os_accounts.create_account(
            settings.TEST_RUNNER_USER, 
            os_accounts.hashpass(settings.TEST_RUNNER_USER),
            max_quota=True)
    reverse_link = reverse('instance-list',
                           args=[os_id.provider.id,
                                 os_id.id])
    os_base_instance_url = urljoin(settings.SERVER_URL, reverse_link)

#def tearDownModule():
class InstanceTests(TestCase):
    api_client = None
    expected_output = {
            "alias":"",
            "alias_hash":"",
            "created_by":"",
            "has_shell":"",
            "has_vnc":"",
            "ip_address":"",
            "machine_alias":"",
            "machine_alias_hash":"",
            "machine_name":"",
            "name":"",
            "size_alias":"",
            "start_date":"",
            "status":"",
            "tags":"",
            "token":"",
        }


    def setUp_API(self):
        #Initialize API
        self.api_client = TokenAPIClient()
        self.api_client.login(
            username=settings.TEST_RUNNER_USER,
            password=settings.TEST_RUNNER_PASS)

    def setUp(self):
        self.setUp_API()

    def tearDown(self):
        self.api_client.logout()

    #def test_openstack_launch(self):
    #    self.os_instance_id, self.os_instance_ip = self.launch_openstack_instance()

    #def test_openstack_stop_start(self):
    #    self.os_instance_id, self.os_instance_ip = self.launch_openstack_instance()
    #    self.instance_action_step(self.os_instance_id, 'stop')
    #    time.sleep(5*60)
    #    self.instance_action_step(self.os_instance_id, 'start')
    #    time.sleep(5*60)

    #def test_openstack_suspend_resume(self):
    #    self.os_instance_id, self.os_instance_ip = self.launch_openstack_instance()
    #    self.instance_action_step(self.os_instance_id, 'suspend')
    #    time.sleep(5*60)
    #    self.instance_action_step(self.os_instance_id, 'resume')
    #    time.sleep(5*60)

    #def test_openstack_resize_and_revert(self):
    #    self.os_instance_id, self.os_instance_ip = self.launch_openstack_instance()
    #    self.instance_action_step(self.os_instance_id, 'resize', {'size':'3'})
    #    time.sleep(7*60)
    #    self.instance_action_step(self.os_instance_id, 'revert_resize')
    #    time.sleep(7*60)

    #def test_openstack_resize_up_and_down(self):
    #    self.os_instance_id, self.os_instance_ip = self.launch_openstack_instance()
    #    self.instance_action_step(self.os_instance_id, 'resize', {'size':'3'})
    #    time.sleep(7*60)
    #    self.instance_action_step(self.os_instance_id, 'confirm_resize')
    #    time.sleep(7*60)
    #    self.instance_action_step(self.os_instance_id, 'resize', {'size':'1'})
    #    time.sleep(7*60)
    #    self.instance_action_step(self.os_instance_id, 'confirm_resize')
    #    time.sleep(7*60)

    def launch_openstack_instance(self):
        """
        Testing instances must be done in order
        * Create the instance
        * Detail the instance
        * Delete the instance
        """
        global delete_instances
        os_instance_id, os_instance_ip = standup_instance(
            self, os_base_instance_url, "0f539197-3718-40bc-8a29-c22e0841684f",
            "1", "Ubuntu 12.04 - Automated OpenStack Testing",
            delete_before=delete_instances)
        if delete_instances:
            delete_instances = False
        return (os_instance_id, os_instance_ip)

    def instance_action_step(self, instance_id, action, action_params={}):
        instance_action_url = urljoin(
            urljoin(os_base_instance_url, '%s/' % instance_id),
            'action/')
        #Attach volume parameters
        action_params.update({
            'action':action,
        })

        action_resp = self.api_client.post(instance_action_url, action_params,
                                           format='json')
        self.assertEqual(action_resp.status_code, status.HTTP_200_OK)
        self.assertEqual('success',
                         action_resp.data.get('result','No Result In Data'))
        return action_resp

    def detail_step_os(self, instance_id):
        #Detail the instance
        os_instance_url = urljoin(
                os_base_instance_url,
                '%s/' % instance_id)
        instance_get_resp = self.api_client.get(os_instance_url)
        #Validate the output
        self.assertEqual(instance_get_resp.status_code, status.HTTP_200_OK)
        verify_expected_output(self, instance_get_resp.data, self.expected_output)

    def predelete_step_os(self):
        list_instance_resp = self.api_client.get(os_base_instance_url)
        self.assertEqual(list_instance_resp.status_code, status.HTTP_200_OK)
        if not list_instance_resp.data:
            return False
        for instance in list_instance_resp.data:
            self.delete_step_os(instance['alias'])
        return True
        
    def delete_step_os(self, instance_id):
        os_instance_url = os.path.join(
                os_base_instance_url,
                '%s/' % instance_id)
        #Delete the instance
        delete_resp = self.api_client.delete(os_instance_url)
        #Validate the output
        self.assertEqual(delete_resp.status_code, status.HTTP_200_OK)

    #def test_euca_instance(self):
    #    """
    #    Testing instances must be done in order
    #    * Create the instance
    #    * Detail the instance
    #    * Delete the instance
    #    # Wait for instance to deploy and
    #    # Ensure: SSH, VNC, Shellinabox, Deploy access
    #    """
    #    euca_launch_data = {
    #        "machine_alias":"emi-E7F8300F",
    #        "size_alias":"m1.small",
    #        "name":"Ubuntu 12.04 - Euca Test",
    #        "tags":['test_tag1','test_tag2','test_tag3']}
    #    self.expected_output['name'] = euca_launch_data['name']
    #    self.expected_output['machine_alias'] = euca_launch_data['machine_alias']
    #    self.expected_output['size_alias'] = euca_launch_data['size_alias']
    #    self.expected_output['tags'] = euca_launch_data['tags']
    #    deleted = self.predelete_step_euca()
    #    #if deleted:
    #    #    # Give it some time to clear, so we dont go over-quota..
    #    #    time.sleep(60*4) # Sorry, its euca.

    #    instance_id = self.launch_step_euca(euca_launch_data)
    #    self.detail_step_euca(instance_id)
    #    #self.delete_step_euca(instance_id)

    #def launch_step_euca(self, euca_launch_data):
    #    #Create the instance
    #    instance_launch_resp = self.api_client.post(self.euca_instance_url, euca_launch_data, format='json')
    #    #Validate the output
    #    self.assertEqual(instance_launch_resp.status_code, status.HTTP_201_CREATED)
    #    self.assertIsNotNone(instance_launch_resp.data)
    #    verify_expected_output(self, instance_launch_resp.data, self.expected_output)
    #    instance_id = instance_launch_resp.data['alias']
    #    return instance_id

    #def predelete_step_euca(self):
    #    list_instance_resp = self.api_client.get(self.euca_instance_url)
    #    self.assertEqual(list_instance_resp.status_code, status.HTTP_200_OK)
    #    if not list_instance_resp.data:
    #        return False
    #    for instance in list_instance_resp.data:
    #        self.delete_step_euca(instance['alias'])
    #    return True

    #def detail_step_euca(self, instance_id):
    #    #Detail the instance
    #    new_euca_instance_url = urljoin(
    #            self.euca_instance_url,
    #            '%s/' % instance_id)
    #    logger.info("Testing on url:%s" % new_euca_instance_url)
    #    instance_get_resp = self.api_client.get(new_euca_instance_url)
    #    logger.info("URL Response: %s" % instance_get_resp)
    #    #Validate the output
    #    self.assertEqual(instance_get_resp.status_code, status.HTTP_200_OK)
    #    verify_expected_output(self, instance_get_resp.data, self.expected_output)

    #def delete_step_euca(self, instance_id):
    #    new_euca_instance_url = urljoin(
    #            self.euca_instance_url,
    #            '%s/' % instance_id)
    #    logger.info("Testing on url:%s" % new_euca_instance_url)
    #    #Delete the instance
    #    delete_resp = self.api_client.delete(new_euca_instance_url)
    #    #Validate the output
    #    self.assertEqual(delete_resp.status_code, status.HTTP_200_OK)


if __name__ == "__main__":
   unittest.main()
