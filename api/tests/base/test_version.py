"""
Tests for base views (i.e. views shared between api versions)
"""
from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase, force_authenticate

from api.base.views import VersionViewSet, DeployVersionViewSet
from api.tests.factories import UserFactory


class VersionTests(APITestCase):
    view_set = VersionViewSet

    def test_get_version(self):
        """
        Test a sucessful response and shape
        """
        user_a = UserFactory.create()
        view = self.view_set.as_view({'get': 'list'})
        request = APIRequestFactory().get("")
        force_authenticate(request, user=user_a)
        response = view(request)
        self.assertEquals(response.status_code, 200)

        data = response.data
        keys = ['git_sha', 'git_sha_abbrev', 'commit_date', 'git_branch']
        for key in keys:
            self.assertIn(key, data)
            self.assertIsNotNone(data[key])


class DeployVersionTests(VersionTests):
    view_set = DeployVersionViewSet
