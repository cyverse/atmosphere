from django.core.urlresolvers import reverse
from django.test import modify_settings
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.tests.factories import UserFactory, AnonymousUserFactory, ProviderFactory
from api.v2.views import TokenUpdateViewSet, IdentityViewSet, CredentialViewSet

class TokenUpdateTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.provider = ProviderFactory.create(location="mock location", type__name="mock")
        self.view = TokenUpdateViewSet.as_view({'post': 'create'})
        self.identity_view = IdentityViewSet.as_view({'get': 'retrieve'})
        self.credentials_view = CredentialViewSet.as_view({'get': 'list'})
        self.token_uuid = "test-token-1234-debug"

    @modify_settings(AUTHENTICATION_BACKENDS={
        'append': 'django_cyverse_auth.authBackends.OpenstackLoginBackend',
    })
    def test_invalid_provider_token_update(self):
        factory = APIRequestFactory()
        url = reverse('api:v2:token_update-list')
        data = {
            'username': self.user.username,
            'project_name': self.user.username,
            'provider': "nopenopenope",
            'token': self.token_uuid
        }
        request = factory.post(url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertTrue(response.status_code == 400)
        self.assertTrue('provider' in response.data)
        self.assertTrue("not a valid UUID" in response.data['provider'][0], "API returned unexpected error message %s" % response.data['provider'][0])

    def test_valid_data_token_update(self):
        factory = APIRequestFactory()
        provider_uuid = str(self.provider.uuid)
        url = reverse('api:v2:token_update-list')
        data = {
            'username': self.user.username,
            'project_name': self.user.username,
            'provider': provider_uuid,
            'token': self.token_uuid
        }
        request = factory.post(url, data)
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEquals(response.status_code, 201)
        data = response.data
        self.assertTrue('identity_uuid' in data)
        identity_uuid = data['identity_uuid']
        cred_url = reverse('api:v2:credential-list')
        cred_request = factory.get(cred_url)
        force_authenticate(cred_request, user=self.user)
        cred_response = self.credentials_view(cred_request)
        self.assertTrue('results' in cred_response.data)
        for cred in cred_response.data['results']:
            self.assertTrue(cred['identity']['uuid'] == identity_uuid)
            if cred['key'] == 'key':
                self.assertTrue(cred['value'] == self.user.username)
            elif cred['key'] == 'ex_project_name':
                self.assertTrue(cred['value'] == self.user.username)
            elif cred['key'] == 'ex_force_auth_token':
                self.assertTrue(cred['value'] == self.token_uuid)
