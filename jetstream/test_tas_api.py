import json

import freezegun
import vcr
from django.test import TestCase
from django.conf import settings
from api.tests.factories import UserFactory

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
        user = UserFactory.create(username='sgregory')
        with freezegun.freeze_time('2016-09-15T05:00:00Z'):
            is_jetstream_valid = jetstream_auth_plugin.validate_user(user)
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

    @my_vcr.use_cassette()
    def test_get_tacc_username_api_problem(self, cassette):
        """Make sure we don't return the Atmosphere username when we have trouble connecting to the TAS API.
        It should fail.

        TODO: Figure out how to handle it gracefully.
        """
        from jetstream.allocation import TASAPIDriver
        tas_driver = TASAPIDriver()
        tas_driver.clear_cache()
        self.assertDictEqual(tas_driver.username_map, {})
        user = UserFactory.create(username='jfischer')
        tacc_username = tas_driver.get_tacc_username(user)
        self.assertIsNone(tacc_username)
        self.assertDictEqual(tas_driver.username_map, {})
        assert_cassette_playback_length(cassette, 1)
