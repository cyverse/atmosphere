from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from api.serializers import ProviderSerializer
from core.factories.group import GroupWithDataFactory


class ProviderTest(APITestCase):
    """
    API Tests for provider endpoints
    """
    def setUp(self):
        # Have group name match the users name
        self.group = GroupWithDataFactory.create(name="test")
        user = self.group.leaders.first()
        self.providers = self.group.providers.all()
        self.provider_data = ProviderSerializer(self.providers).data
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def test_get_provider_list(self):
        """
        Returns a list of providers
        """
        url = reverse("api:public_apis:provider-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.provider_data)

    def test_get_provider_list_with_404(self):
        for provider in self.providers:
            provider.unshare(self.group)
        url = reverse("api:public_apis:provider-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_provider_detail(self):
        """
        Returns a provider
        """
        url = reverse("api:public_apis:provider-detail",
                      args=(self.providers[0].uuid,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.provider_data[0])

    def test_get_provider_detail_with_404(self):
        self.providers[0].unshare(self.group)
        url = reverse("api:public_apis:provider-detail",
                      args=(self.providers[0].uuid,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
