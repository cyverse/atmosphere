from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest

import json

from rest_framework import status
from rest_framework.test import APIClient
from urlparse import urljoin

from atmosphere import settings
from api.tests import verify_expected_output
from core.tests import create_euca_provider, create_os_provider
from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts


class TokenAPIClient(APIClient):
    token = None

    def ldap_new_token(self, client, **credentials):
        """
        Authenticate **credentials, create a token and return the tokens uuid
        """
        reverse_url = reverse('token-auth')
        data = {
            "username":credentials.get('username'),
            "password":credentials.get('password'),
            }
        full_url = urljoin(settings.SERVER_URL, reverse_url)
        response = client.post(full_url, data, format='multipart')
        json_data = json.loads(response.content)
        return json_data


    def login(self, **credentials):
        logged_in = super(TokenAPIClient, self).login(**credentials)
        if not logged_in:
            return False
        self.token = self.ldap_new_token(self, **credentials)
        if not self.token:
            return False
        self.credentials(HTTP_AUTHORIZATION='Token %s' % self.token['token'])
        return True

class AuthTests(TestCase):
    client = None

    expected_output = {
        "username":"",
        "token":"",
        "expires":"",
        }

    def setUp(self):
        #Initialize API
        self.euca_admin_id = create_euca_provider()
        self.euca_provider = self.euca_admin_id.provider
        euca_accounts = EucaAccounts(self.euca_provider)
        euca_user = euca_accounts.get_user(settings.TEST_RUNNER_USER)
        self.euca_id = euca_accounts.create_account(euca_user)
        self.client = TokenAPIClient()
        self.client.login(
                username=settings.TEST_RUNNER_USER,
                password=settings.TEST_RUNNER_PASS)

    def tearDown(self):
        self.client.logout()

    def test_token_output(self):
        """
        Explicitly call auth and test that tokens can be created.
        """
        verify_expected_output(self, self.client.token, self.expected_output)

