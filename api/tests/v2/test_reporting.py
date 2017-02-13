import json
from unittest import skip, skipUnless

from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from api.tests.factories import UserFactory, AnonymousUserFactory
from api.v2.views import ReportingViewSet
from core.models import AtmosphereUser


def contains_user(username):
    """
    Test if the username exists
    """
    try:
        AtmosphereUser.objects.get_by_natural_key(username=username)
        return True
    except AtmosphereUser.DoesNotExist:
        return False


class ReportingTests(APITestCase):
    def setUp(self):
        self.anonymous_user = AnonymousUserFactory()
        self.user = UserFactory.create()
        self.view = ReportingViewSet.as_view({'get': 'list'})

    #def test_long_history_pull_excel_file(self):
    #    """Will only work with a correct database."""
    #    factory = APIRequestFactory()
    #    url = '/api/v2/reporting?format=xlsx&start_date=2015-01-01&end_date=2017-01-28&provider_id=4&provider_id=5&provider_id=6'
    #    request = factory.get(url)
    #    sanity_user = AtmosphereUser.objects.get_by_natural_key('sgregory')
    #    force_authenticate(request, user=sanity_user)
    #    response = self.view(request)
    #    self.assertEquals(response.status_code, 200)
    #    self.assertEquals(response.accepted_media_type, 'application/vnd.ms-excel')
    #    with open('/opt/dev/atmosphere/reporting.xlsx','wb') as reporting_file:
    #        for chunk in response.rendered_content:
    #            reporting_file.write(chunk)
    #        reporting_file.flush()
    #    return

    #@skipUnless(contains_user('test-julianp'), 'The database does not contain the user test-julianp')
    @skip('skip for now')
    def test_a_sanity_check(self):
        """Will only work with a correct database.
        TODO: Create providers and fixtures necessary to get working.
        """
        factory = APIRequestFactory()
        url = '/api/v2/reporting?start_date=2016-01-01&end_date=2016-10-25&provider_id=1&provider_id=2&provider_id=3&' \
              'provider_id=4&provider_id=5&provider_id=6'
        request = factory.get(url)
        sanity_user = AtmosphereUser.objects.get_by_natural_key('test-julianp')
        force_authenticate(request, user=sanity_user)
        response = self.view(request)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.data), 1)
        received_data = json.loads(json.dumps(response.data, indent=2))
        expected_data_json = '''[
      {
        "id": 29792,
        "instance_id": "57259394-a1d2-4318-a0c0-5764f42db4be",
        "username": "test-julianp",
        "staff_user": "False",
        "provider": "iPlant Workshop Cloud - Tucson",
        "image_name": "Ubuntu 14.04.2 XFCE Base",
        "version_name": "1.0",
        "is_featured_image": true,
        "hit_aborted": false,
        "hit_active_or_aborted": 1,
        "hit_active_or_aborted_or_error": 1,
        "hit_active": true,
        "hit_deploy_error": false,
        "hit_error": false,
        "size": {
          "id": 105,
          "uuid": "60fccf16-d0ba-488d-b8a5-46a9752dc2ca",
          "url": "http://testserver/api/v2/sizes/60fccf16-d0ba-488d-b8a5-46a9752dc2ca",
          "alias": "1",
          "name": "tiny1",
          "cpu": 1,
          "disk": 0,
          "mem": 4096,
          "active": true,
          "start_date": "2014-06-06T20:50:08.387646Z",
          "end_date": null
        },
        "start_date": "09/20/16 17:36:57",
        "end_date": null
      }
    ]'''
        expected_data = json.loads(expected_data_json)
        dict_eq_(self, received_data, expected_data)

    def test_is_not_public(self):
        factory = APIRequestFactory()
        url = reverse('api:v2:reporting-list')
        request = factory.get(url)
        force_authenticate(request, user=self.anonymous_user)
        response = self.view(request)
        self.assertEquals(response.status_code, 403)

    def test_no_query_params(self):
        factory = APIRequestFactory()
        url = reverse('api:v2:reporting-list')
        request = factory.get(url)
        force_authenticate(request, user=self.user)
        response = self.view(request)
        self.assertEquals(response.status_code, 400)
        self.assertEqual(response.data['errors'][0]['message'],
                         "The reporting API should be accessed via the query parameters:"
                         " ['start_date', 'end_date', 'provider_id']")

    def test_invalid_query_params(self):
        factory = APIRequestFactory()
        invalid_urls = [
            'api/v2/reporting?start_date=3077-10-29&end_date=1901-10-29&provider_id=some_provider',
            'api/v2/reporting?start_date=blah&end_date=1901-10-29&provider_id=1',
            'api/v2/reporting?start_date=3077-10-29&end_date=blah&provider_id=1'
        ]
        for url in invalid_urls:
            request = factory.get(url)
            force_authenticate(request, user=self.user)
            response = self.view(request)
            self.assertEquals(response.status_code, 400)
            self.assertEqual(response.data['errors'][0]['message'], 'Invalid filter parameters')

    @skip('skip for now')
    def test_access_invalid_provider(self):
        raise NotImplementedError

    @skip('skip for now')
    def test_access_not_allowed_provider(self):
        raise NotImplementedError
