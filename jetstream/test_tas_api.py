import json

import vcr
from django.test import TestCase
from django.conf import settings
from mock import Mock

from test_utils.cassette_utils import assert_cassette_playback_length, scrub_host_name

my_vcr = vcr.VCR(
    before_record=scrub_host_name,
    path_transformer=vcr.VCR.ensure_suffix('.yaml'),
    cassette_library_dir='jetstream/fixtures',
    filter_headers=[('Authorization', 'Basic XXXXX')],
    inject_cassette=True
)


class TestJetstream(TestCase):
    """Tests for Jetstream allocation source API"""

    def setUp(self):
        if 'jetstream' not in settings.INSTALLED_APPS:
            self.skipTest('jetstream not in settings.INSTALLED_APPS')

    @my_vcr.use_cassette()
    def test_validate_account(self, cassette):
        """Test for a valid account based on the business logic assigned by Jetstream"""
        from jetstream.plugins.auth.validation import XsedeProjectRequired
        jetstream_auth_plugin = XsedeProjectRequired()
        mock_user = Mock()
        mock_user.username = 'sgregory'
        is_jetstream_valid = jetstream_auth_plugin.validate_user(mock_user)
        self.assertTrue(is_jetstream_valid)
        assert_cassette_playback_length(cassette, 2)

    @my_vcr.use_cassette()
    def test_get_all_allocations(self, cassette):
        """Test retrieving allocations for a Jetstream user"""
        from jetstream.allocation import TASAPIDriver
        tas_driver = TASAPIDriver()
        allocations = tas_driver.get_all_allocations()

        self.assertEquals(len(allocations), 2)
        self.maxDiff = None
        self.assertEquals(allocations[0]['project'], u'CH-916862')
        self.assertEquals(allocations[-1]['project'], u'TG-MCB960139')

        response = json.loads(cassette.data[0][1]['body']['string'])
        result = response['result']
        self.assertEquals(len(allocations), len(result))
        self.assertEquals(allocations[0], result[0])
        self.assertEquals(allocations[-1], result[-1])

        assert_cassette_playback_length(cassette, 1)

    @my_vcr.use_cassette()
    def test_get_all_projects(self, cassette):
        """Test retrieving projects for a Jetstream user"""
        from jetstream.allocation import TASAPIDriver
        tas_driver = TASAPIDriver()
        projects = tas_driver.get_all_projects()

        self.assertEquals(len(projects), 2)
        self.assertEquals(projects[0]['chargeCode'], u'CH-916862')
        self.assertEquals(projects[-1]['chargeCode'], u'TG-MCB960139')
        self.maxDiff = None
        response = json.loads(cassette.data[0][1]['body']['string'])
        result = response['result']
        self.assertEquals(len(projects), len(result))
        self.assertEquals(projects[0], result[0])
        self.assertEquals(projects[-1], result[-1])

        assert_cassette_playback_length(cassette, 1)
