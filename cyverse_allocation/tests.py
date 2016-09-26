from django.test import TestCase
from django.conf import settings


# Create your tests here.

class CyVerseAllocationTests(TestCase):
    def setUp(self):
        if 'cyverse_allocation' not in settings.INSTALLED_APPS:
            self.skipTest('CyVerse Allocation plugin is not enabled')

    def test_failing(self):
        pass
        # raise NotImplementedError
