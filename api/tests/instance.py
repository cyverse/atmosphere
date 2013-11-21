from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest

from rest_framework import status
from rest_framework.test import APIClient

from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts
from core.tests import create_euca_provider, create_os_provider

class InstanceTests(TestCase):
    client = None

    def setUp(self):
        #Initialize core DB
        self.euca_admin_id = create_euca_provider()
        self.euca_provider = euca_admin_id.provider
        self.os_admin_id = create_os_provider()
        self.os_provider = os_admin_id.provider
        #Initialize API
        self.client = APIClient()
        self.client.login(username='estevetest03',
                     password='testtest')
        os_accounts = OSAccounts(self.os_provider)
        self.os_identity = os_accounts.create_account('estevetest03', os_accounts.hashpass('estevetest03'))
        

    def tearDown(self):
        client.logout()

    def test_create_instance(self):
        """
        Ensure we can create a new instance via API.
        """
        url = reverse('identity-list')
        data = {'name': 'DabApps'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, data)
        #Check instance url

