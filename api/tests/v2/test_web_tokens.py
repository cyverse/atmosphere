from django.urls import resolve
from rest_framework.test import APITestCase


class WebTokenTests(APITestCase):
    def test_url_resolution(self):
        """
        Url config correctly resolves uuids
        """
        match = resolve('/api/v2/web_tokens/d71e6b24-841e-4b77-a819-01098579e6a9')

        # Assert that a match exists (that the result is truthy)
        self.assertTrue(match)
