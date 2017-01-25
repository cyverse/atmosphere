from rest_framework.test import APITestCase
from api.tests.factories import UserFactory, AnonymousUserFactory

class AuthTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.username = "test-user"
        self.password = "test-password"
        self.user = UserFactory.create(username=self.username)
        self.user.set_password(self.password)
        self.auth_url = "/auth"

    def test_invalid_openstack_auth(self):
        data = {
            'username': self.username,
            'password': self.password,
            'project_name': self.username,
            'auth_url': "https://fake.cloud.atmosphere"
        }
        response = self.client.post(self.auth_url, data)
        resp_data = response.data
        self.assertEquals(response.status_code, 400)
        self.assertTrue('errors' in resp_data)
        self.assertTrue('message' in resp_data['errors'][0])
        err_message = resp_data['errors'][0]['message']
        self.assertTrue("Username/Password combination was invalid" in err_message)

    #TODO: This will *ONLY* work if OpenstackLoginBackend is in settings.AUTHENTICATION_BACKENDS *AND* the credentials are valid
    # def test_valid_openstack_auth(self):
    #     data = {
    #         'username': self.username,
    #         'password': self.password,
    #         'project_name': self.username,
    #         'auth_url': "https://real.cloud.atmosphere"
    #     }
    #     response = self.client.post(self.auth_url, data)
    #     resp_data = response.data
    #     self.assertEquals(response.status_code, 201)
    #     self.assertTrue(resp_data['username'] == test_username)
    #     self.assertTrue(resp_data['token'] != None)

    #TODO: This will *ONLY* work if ModelLoginBackend is in settings.AUTHENTICATION_BACKENDS
    # def test_valid_model_auth(self):
    #     data = {
    #         'username': self.username,
    #         'password': self.password,
    #     }
    #     response = self.client.post(self.auth_url, data)
    #     self.assertEquals(response.status_code, 201)
    #     data = response.data

    #TODO: This will *ONLY* work if LDAPLoginBackend is properly setup *AND* you use a valid set of credentials
    # def test_valid_ldap_auth(self):
    #     test_username = "sgregory-test"
    #     test_password = "fake_password"
    #     data = {
    #         'username': test_username,
    #         'password': test_password
    #     }
    #     response = self.client.post(self.auth_url, data)
    #     resp_data = response.data
    #     self.assertEquals(response.status_code, 201)
    #     self.assertTrue(resp_data['username'] == test_username)
    #     self.assertTrue(resp_data['token'] != None)

    def test_invalid_ldap_auth(self):
        test_username = "sgregory-test"
        test_password = "fake_password"
        data = {
            'username': test_username,
            'password': test_password
        }
        response = self.client.post(self.auth_url, data)
        resp_data = response.data
        self.assertEquals(response.status_code, 400)
        self.assertTrue('errors' in resp_data)
        self.assertTrue('message' in resp_data['errors'][0])
        err_message = resp_data['errors'][0]['message']
        self.assertTrue("Username/Password combination was invalid" in err_message)



