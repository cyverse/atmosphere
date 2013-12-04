from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest

import os

from rest_framework import status
from threepio import logger
from urlparse import urljoin

from atmosphere import settings
from core.tests import create_euca_provider, create_os_provider
from api.tests import verify_expected_output
from api.tests.test_auth import TokenAPIClient
from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts

#class MachineTests(TestCase):
#    api_client = None
#    expected_output = {
#        "alias": "", 
#        "alias_hash": "", 
#        "created_by": "", 
#        "icon": "",
#        "private": "",
#        "architecture": "", 
#        "ownerid": "", 
#        "state": "", 
#        "name": "", 
#        "tags": "", 
#        "description": "", 
#        "start_date": "", 
#        "end_date": "", 
#        "featured": "", 
#        "identifier": "", 
#        "created_by_identity": ""
#    }
#    def setUp(self):
#        #Initialize core DB
#        self.euca_admin_id = create_euca_provider()
#        self.euca_provider = self.euca_admin_id.provider
#        self.os_admin_id = create_os_provider()
#        self.os_provider = self.os_admin_id.provider
#        #Ensure there is an account created/ready to go
#        euca_accounts = EucaAccounts(self.euca_provider)
#        euca_user = euca_accounts.get_user(settings.TEST_RUNNER_USER)
#        self.euca_id = euca_accounts.create_account(euca_user)
#        os_accounts = OSAccounts(self.os_provider)
#        self.os_id = os_accounts.create_account(
#                settings.TEST_RUNNER_USER, 
#                os_accounts.hashpass(settings.TEST_RUNNER_USER))
#        #Initialize API
#        self.api_client = TokenAPIClient()
#        self.api_client.login(
#                username=settings.TEST_RUNNER_USER,
#                password=settings.TEST_RUNNER_PASS)
#        reverse_link = reverse('machine-list',
#                               args=[self.os_id.provider.id,
#                                     self.os_id.id])
#        self.os_machine_url = urljoin(settings.SERVER_URL, reverse_link)
#        reverse_link = reverse('machine-list',
#                              args=[self.euca_id.provider.id,
#                                    self.euca_id.id])
#        self.euca_machine_url = urljoin(settings.SERVER_URL, reverse_link)
#        
#
#    def tearDown(self):
#        self.api_client.logout()
#
#    def test_euca_machine(self):
#        """
#        Testing machines must be done in order
#        * Create the machine
#        * Detail the machine
#        * Delete the machine
#        # Wait for machine to deploy and
#        # Ensure: SSH, VNC, Shellinabox, Deploy access
#        """
#        list_machine_resp = self.api_client.get(self.euca_machine_url)
#        self.assertEqual(list_machine_resp.status_code, status.HTTP_200_OK)
#        if not list_machine_resp.data:
#            return
#        for machine in list_machine_resp.data:
#            verify_expected_output(self, machine, self.expected_output)
#
#    def test_openstack_machine(self):
#        """
#        Testing machines must be done in order
#        * Create the machine
#        * Detail the machine
#        * Delete the machine
#        """
#        list_machine_resp = self.api_client.get(self.os_machine_url)
#        self.assertEqual(list_machine_resp.status_code, status.HTTP_200_OK)
#        if not list_machine_resp.data:
#            return
#        for machine in list_machine_resp.data:
#            verify_expected_output(self, machine, self.expected_output)
#
#
#if __name__ == "__main__":
#   unittest.main()
#
