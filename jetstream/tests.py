import json

from django.test import TestCase

import vcr


class TestJetstream(TestCase):
    def setUp(self):
        pass

    @vcr.use_cassette('jetstream/fixtures/test_validate_account.yaml', inject_cassette=True,
                      filter_headers=[('Authorization', 'Basic XXXXX')])
    def test_validate_account(self, cassette):
        from jetstream.plugins.auth.validation import validate_account
        is_jetstream_valid = validate_account('sgregory')
        self.assertTrue(is_jetstream_valid)
        self.assertTrue(cassette.all_played)

    @vcr.use_cassette('jetstream/fixtures/test_get_all_allocations.yaml', inject_cassette=True,
                      filter_headers=[('Authorization', 'Basic XXXXX')])
    def test_get_all_allocations(self, cassette):
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

    @vcr.use_cassette('jetstream/fixtures/test_get_all_projects.yaml', inject_cassette=True,
                      filter_headers=[('Authorization', 'Basic XXXXX')])
    def test_get_all_projects(self, cassette):
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
