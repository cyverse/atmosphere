from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest

import json

from rest_framework import status
from rest_framework.test import APIClient
from urlparse import urljoin

from atmosphere import settings
from atmosphere.settings import secrets
from api.tests import verify_expected_output
from authentication.protocol.oauth import generate_access_token
from core.tests import create_euca_provider, create_os_provider
from service.accounts.openstack import AccountDriver as OSAccounts
from service.accounts.eucalyptus import AccountDriver as EucaAccounts


class OAuthTokenAPIClient(APIClient):
    token = None

    def oauth_token_test(self, api_client, **credentials):
        """
        Authenticate **credentials, create a token and return the tokens uuid
        """
        oauth_token = "JHbSqjRVfp8k_BRWZtVkr4L-0By1cDGB1-XiJ4bkej3kl8x-Mc_nwZFJ"
        reverse_url = reverse('profile')
        full_url = urljoin(settings.SERVER_URL, reverse_url)
        api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + oauth_token)
        response = api_client.get(full_url, data, format='multipart')
        json_data = json.loads(response.content)
        return json_data


    def login(self, **credentials):
        username = credentials.get('oauth_user')
        if not username:
            return False
        token, expires = generate_access_token(
            open(secrets.OAUTH_PRIVATE_KEY).read(),
            iss=secrets.OAUTH_ISSUE_USER,
            scope=secrets.OAUTH_SCOPE,
            sub=username)
        if not token:
            raise Exception("Cannot generate OAuth Access token to atmosphere"
                            " service for user:%s. Check the Secrets file")
        #This is what a successful /auth response looks like..
        #TODO: See if we can use a serializer here to keep results consistent
        # with changes in /auth URL
        self.token = {
                'username': username,
                'token' : token,
                'expires': expires
                }
        if not self.token:
            return False
        self.credentials(HTTP_AUTHORIZATION='Bearer %s' % self.token['token'])
        return True

class TokenAPIClient(APIClient):
    token = None

    def ldap_new_token(self, api_client, **credentials):
        """
        Authenticate **credentials, create a token and return the tokens uuid
        """
        reverse_url = reverse('token-auth')
        data = {
            "username":credentials.get('username'),
            "password":credentials.get('password'),
            }
        full_url = urljoin(settings.SERVER_URL, reverse_url)
        response = api_client.post(full_url, data, format='multipart')
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
    api_client = None

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

    def tearDown(self):
        pass

    def test_oauth_token(self):
        """
        Explicitly call auth and test that tokens can be created.
        """
        self.oauth_api_client = OAuthTokenAPIClient()
        self.oauth_api_client.login(oauth_user='sgregory')
        verify_expected_output(self, self.oauth_api_client.token, self.expected_output)
        self.oauth_api_client.logout()

    def test_api_token(self):
        """
        Explicitly call auth and test that tokens can be created.
        """
        self.api_client = TokenAPIClient()
        self.api_client.login(
                username=settings.TEST_RUNNER_USER,
                password=settings.TEST_RUNNER_PASS)
        verify_expected_output(self, self.api_client.token, self.expected_output)
        self.api_client.logout()

