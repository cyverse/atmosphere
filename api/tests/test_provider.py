from django.utils import unittest
from django.core.urlresolvers import reverse

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from api.serializers import ProviderSerializer
from core.query import only_current_provider
from core.factories.group import GroupWithDataFactory
from core.models import Provider

@unittest.skip("Update test since ProviderMachine was removed!")
class ProviderTest(APITestCase):
    """
    API Tests for provider endpoints
    """
    def setUp(self):
        # Have group name match the users name
        self.group = GroupWithDataFactory.create(name="test")
        #TODO: Create IDENTITIES to use 'self.providers'
        user = self.group.leaders.first()
        provider_ids = self.group.identities.filter(only_current_provider(), provider__active=True).values_list('provider', flat=True)
        self.providers = Provider.objects.filter(id__in=provider_ids)
        self.provider_data = ProviderSerializer(self.providers, many=True).data
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

    @unittest.expectedFailure
    def test_get_provider_list_with_404(self):
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
        url = reverse("api:public_apis:provider-detail",
                      args=(self.providers[0].uuid,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
