import mock
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APITestCase

from api.tests.factories import UserFactory, AnonymousUserFactory
from core.models import AtmosphereUser


class OverrideLoginBackend():
    def __init__(self, *args, **kwargs):
        pass

    def authenticate(self, username=None, password=None, *args, **kwargs):       # Authenticate username/password if the user exists, otherwise create it
        user = None
        try:
            user = AtmosphereUser.objects.get(username=username)
            if user.check_password(password):
                return user
        except:
            user = AtmosphereUser.objects.create(username=username)
            user.set_password(password)
            user.save()
        return user


class AuthTests(APITestCase):

    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.username = "test-user"
        self.password = "test-password"
        self.user = UserFactory.create(username=self.username)
        self.user.set_password(self.password)
        self.user.save()
        self.auth_url = "/auth"

    @override_settings(AUTHENTICATION_BACKENDS=('django_cyverse_auth.authBackends.OpenstackLoginBackend',))
    @mock.patch('django_cyverse_auth.authBackends.OpenstackLoginBackend', side_effect=OverrideLoginBackend)
    def test_valid_openstack_auth(self, patch_func):
        if 'django_cyverse_auth.authBackends.OpenstackLoginBackend' not in settings.AUTHENTICATION_BACKENDS:
            self.skipTest('django_cyverse_auth.authBackends.OpenstackLoginBackend not in settings.AUTHENTICATION_BACKENDS')
        data = {
            'username': self.username,
            'password': self.password,
            'project_name': self.username,
            'auth_url': "localhost"
        }
        response = self.client.post(self.auth_url, data)
        resp_data = response.data
        self.assertEquals(response.status_code, 201)
        self.assertTrue(resp_data['username'] == self.username)
        self.assertTrue(resp_data['token'] is not None)

    @override_settings(AUTHENTICATION_BACKENDS=('django_cyverse_auth.authBackends.OpenstackLoginBackend',))
    def test_invalid_openstack_auth(self):
        if 'django_cyverse_auth.authBackends.OpenstackLoginBackend' not in settings.AUTHENTICATION_BACKENDS:
            self.skipTest('django_cyverse_auth.authBackends.OpenstackLoginBackend not in settings.AUTHENTICATION_BACKENDS')
        data = {
            'username': self.username,
            'password': self.password,
            'project_name': self.username,
            'auth_url': "localhost"
        }
        response = self.client.post(self.auth_url, data)
        resp_data = response.data
        self.assertEquals(response.status_code, 400)
        self.assertTrue('errors' in resp_data)
        self.assertTrue('message' in resp_data['errors'][0])
        err_message = resp_data['errors'][0]['message']
        self.assertTrue("Username/Password combination was invalid" in err_message)

    @override_settings(AUTHENTICATION_BACKENDS=('django_cyverse_auth.authBackends.LDAPLoginBackend',))
    @mock.patch('django_cyverse_auth.authBackends.LDAPLoginBackend', side_effect=OverrideLoginBackend)
    def test_valid_ldap_auth(self, patch_func):
        if 'django_cyverse_auth.authBackends.LDAPLoginBackend' not in settings.AUTHENTICATION_BACKENDS:
            self.skipTest('django_cyverse_auth.authBackends.LDAPLoginBackend not in settings.AUTHENTICATION_BACKENDS')
        data = {
            'username': self.username,
            'password': self.password
        }
        response = self.client.post(self.auth_url, data)
        resp_data = response.data
        self.assertEquals(response.status_code, 201)
        self.assertTrue(resp_data['username'] == self.username, "Response returned unexpected username <%s>, expected %s" % (resp_data['username'], self.username))
        self.assertTrue(resp_data['token'] is not None)

    @override_settings(AUTHENTICATION_BACKENDS=('django_cyverse_auth.authBackends.LDAPLoginBackend',))
    def test_invalid_ldap_auth(self):
        if 'django_cyverse_auth.authBackends.LDAPLoginBackend' not in settings.AUTHENTICATION_BACKENDS:
            self.skipTest('django_cyverse_auth.authBackends.LDAPLoginBackend not in settings.AUTHENTICATION_BACKENDS')
        data = {
            'username': self.username,
            'password': self.password
        }
        response = self.client.post(self.auth_url, data)
        resp_data = response.data
        self.assertEquals(response.status_code, 400)
        self.assertTrue('errors' in resp_data)
        self.assertTrue('message' in resp_data['errors'][0])
        err_message = resp_data['errors'][0]['message']
        self.assertTrue("Username/Password combination was invalid" in err_message)

    @override_settings(AUTHENTICATION_BACKENDS=('django.contrib.auth.backends.ModelBackend',))
    def test_valid_model_auth(self):
        if 'django.contrib.auth.backends.ModelBackend' not in settings.AUTHENTICATION_BACKENDS:
            self.skipTest('django.contrib.auth.backends.ModelBackend not in settings.AUTHENTICATION_BACKENDS')
        data = {
            'username': self.username,
            'password': self.password,
        }
        response = self.client.post(self.auth_url, data)
        self.assertEquals(response.status_code, 201)
        data = response.data
