import json
from urlparse import urlparse

import vcr
from django.test import TestCase


def scrub_host_name(request):
    """Replaces any host name with 'localhost'"""
    parse_result = urlparse(request.uri)
    # noinspection PyProtectedMember
    scrubbed_parts = parse_result._replace(netloc='localhost')
    request.uri = scrubbed_parts.geturl()
    return request


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
        pass

    @my_vcr.use_cassette()
    def test_validate_account(self, cassette):
        """Test for a valid account based on the business logic assigned by Jetstream"""
        from jetstream.plugins.auth.validation import validate_account
        is_jetstream_valid = validate_account('sgregory')
        self.assertTrue(is_jetstream_valid)
        self.assertTrue(cassette.all_played)

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
        self.assertTrue(cassette.all_played)

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
