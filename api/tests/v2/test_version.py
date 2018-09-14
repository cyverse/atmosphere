from django.test import TestCase

from api.base.views import VersionViewSet, DeployVersionViewSet
from api.tests.test_pattern_matches_viewset import PatternMatchesViewsetTest


class VersionSanityTests(TestCase, PatternMatchesViewsetTest):
    def test_pattern_matches_viewset(self):
        super(self.__class__, self).test_pattern_matches_viewset(
            'api:v2:version-atmo-list', VersionViewSet
        )


class DeployVersionSanityTests(TestCase, PatternMatchesViewsetTest):
    def test_pattern_matches_viewset(self):
        super(self.__class__, self).test_pattern_matches_viewset(
            'api:v2:version-deploy-list', DeployVersionViewSet
        )
