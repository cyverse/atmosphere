from django.utils import unittest
from django.test import TestCase
from core.models import credential
import json

from atmosphere import settings

from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts

from core.models import ProviderCredential, ProviderType, Provider, Identity

class ServiceTests(TestCase):
    '''
    Test service.*
    '''

    def setUp(self):
        euca_admin_id = self.create_euca_provider()
        os_admin_id = self.create_os_provider()

    def tearDown(self):
        pass

    def test_openstack_account_creation(self):
        provider = Provider.objects.get(location='OPENSTACK')
        os_accounts = OSAccounts(provider)
        new_identity = os_accounts.create_account('test_user', 'test_pass',
        'test_project')
        credentials = new_identity.credential_set.all()
        self.assertEqual(
                credentials.get(key='key').value, 'test_user',
                'Key credential does not match username')
        self.assertEqual(
                credentials.get(key='secret').value, 'test_pass',
                'Secret credential does not match password')
        self.assertEqual(
                credentials.get(key='ex_project_name').value, 'test_project',
                'ex_project_name credential does not match project name')
        self.assertIsNotNone(
                os_accounts.get_user('test_user'),
                'Expected user, got None')
        self.assertIsNotNone(
                os_accounts.get_project('test_project'),
                'Expected project, got None')
        self.assertIsNone(
                os_accounts.get_project('test_user'),
                'A usergroup was created when project was specified')

        os_accounts.delete_account('test_user', 'test_project')

    def test_eucalyptus_identity_creation(self):
        username = 'estevetest03'
        provider = Provider.objects.get(location='EUCALYPTUS')
        accounts = EucaAccounts(provider)
        user = accounts.get_user(username)
        self.assertIsNotNone(
                user, 'Expected user %s exists in eucalyptus, got None' % username)
        identity = accounts.delete_user(username)
        self.assertIsNotNone(
                identity, 'Expected new identity for %s, got None' % identity)
        identity = accounts.create_identity(user)
        accounts.delete_identity(username)
        self.assertEqual(1,1,"Account deleted succesfully")

    def create_euca_provider(self):
        provider_type = ProviderType.objects.get_or_create(name='Eucalyptus')[0]
        euca = Provider.objects.get_or_create(location='EUCALYPTUS',
                                              type=provider_type)[0]
        ProviderCredential.objects.get_or_create(
            key='ec2_url', value=settings.EUCA_EC2_URL, provider=euca)
        ProviderCredential.objects.get_or_create(
            key='s3_url', value=settings.EUCA_S3_URL, provider=euca)
        ProviderCredential.objects.get_or_create(
            key='euca_cert_path', value=settings.EUCALYPTUS_CERT_PATH,
             provider=euca)
        ProviderCredential.objects.get_or_create(
            key='pk_path', value=settings.EUCA_PRIVATE_KEY,
             provider=euca)
        ProviderCredential.objects.get_or_create(
            key='ec2_cert_path', value=settings.EC2_CERT_PATH,
             provider=euca)
        ProviderCredential.objects.get_or_create(
            key='account_path', value='/services/Accounts',
             provider=euca)
        ProviderCredential.objects.get_or_create(
            key='config_path', value='/services/Configuration',
             provider=euca)
        identity = Identity.create_identity('admin', euca.location,
            account_admin=True,
            cred_key=settings.EUCA_ADMIN_KEY,
            cred_secret=settings.EUCA_ADMIN_SECRET)
        return identity

    def create_os_provider(self):
        provider_type = ProviderType.objects.get_or_create(name='OpenStack')[0]
        openstack = Provider.objects.get_or_create(
                location='OPENSTACK',
                type=provider_type)[0]
        ProviderCredential.objects.get_or_create(key='auth_url',
                value=settings.OPENSTACK_AUTH_URL, provider=openstack)
        ProviderCredential.objects.get_or_create(key='admin_url',
                value=settings.OPENSTACK_ADMIN_URL, provider=openstack)
        ProviderCredential.objects.get_or_create(key='router_name',
                value=settings.OPENSTACK_DEFAULT_ROUTER, provider=openstack)
        ProviderCredential.objects.get_or_create(key='region_name',
                value=settings.OPENSTACK_DEFAULT_REGION, provider=openstack)
        identity = Identity.create_identity(
            settings.OPENSTACK_ARGS['username'],
            openstack.location, account_admin=True,
            cred_key=settings.OPENSTACK_ADMIN_KEY,
            cred_secret=settings.OPENSTACK_ADMIN_SECRET,
            cred_ex_tenant_name=settings.OPENSTACK_ADMIN_TENANT,
            cred_ex_project_name=settings.OPENSTACK_ADMIN_TENANT)
        return identity
