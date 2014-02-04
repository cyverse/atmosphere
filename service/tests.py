from django.utils import unittest
from django.test import TestCase
from core.models import credential
import json

from atmosphere import settings

from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts

from core.models import ProviderCredential, ProviderType, Provider, Identity
from core.tests import create_euca_provider, create_os_provider


class ServiceTests(TestCase):
    '''
    Test service.*
    '''

    def setUp(self):
        self.euca_admin_id = create_euca_provider()
        self.euca_provider = self.euca_admin_id.provider
        self.os_admin_id = create_os_provider()
        self.os_provider = self.os_admin_id.provider

    def tearDown(self):
        pass

    #def test_openstack_account_creation(self):
    #    os_accounts = OSAccounts(self.os_provider)
    #    new_identity = os_accounts.create_account(
    #            'test_user', 'test_pass', 'test_project')
    #    credentials = new_identity.credential_set.all()
    #    self.assertEqual(
    #            credentials.get(key='key').value, 'test_user',
    #            'Key credential does not match username')
    #    self.assertEqual(
    #            credentials.get(key='secret').value, 'test_pass',
    #            'Secret credential does not match password')
    #    self.assertEqual(
    #            credentials.get(key='ex_project_name').value, 'test_project',
    #            'ex_project_name credential does not match project name')
    #    self.assertIsNotNone(
    #            os_accounts.get_user('test_user'),
    #            'Expected user, got None')
    #    self.assertIsNotNone(
    #            os_accounts.get_project('test_project'),
    #            'Expected project, got None')
    #    self.assertIsNone(
    #            os_accounts.get_project('test_user'),
    #            'A usergroup was created when project was specified')
    #    #TODO: This line fails with: Unauthorized: Could not find token:
    #    # 91c0731932f04ec5aa6d17c9a7974fba (HTTP 401)
    #    os_accounts.delete_account('test_user', 'test_project')
    #    #Test account was deleted

    def test_eucalyptus_identity_creation(self):
        pass
        #username = 'estevetest03'
        #accounts = EucaAccounts(self.euca_provider)
        #user = accounts.get_user(username)
        #self.assertIsNotNone(
        #        user,
        #        'Expected user %s exists in eucalyptus, got None' % username)
        #identity = accounts.delete_user(username)
        #self.assertIsNotNone(
        #        identity,
        #        'Expected new identity for %s, got None' % identity)
        #identity = accounts.create_identity(user)
        #accounts.delete_identity(username)
        #self.assertEqual(1,1,"Account deleted succesfully")
