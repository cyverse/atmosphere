from django.core.urlresolvers import reverse

from rest_framework.test import APIClient, APIRequestFactory, force_authenticate


class APISanityTestCase(object):
    url_route = None
    user = None

    def test_list_response_is_paginated(self):
        """
        Sanity test -- this should 'just work'
        """
        factory = APIRequestFactory()
        url_route = self.url_route + "-list"
        list_url = reverse(url_route)
        self.list_request = factory.get(list_url)
        force_authenticate(self.list_request, user=self.user)
        list_response = self.list_view(self.list_request)
        self.assertIn(
            'count', list_response.data,
            "Expected list response to be paginated, received: %s"
            % list_response.data)
        self.assertIn(
            'results', list_response.data,
            "Expected list response to be paginated, received: %s"
            % list_response.data)

    def test_detail_endpoints_invalid_data(self):
        """
        This preliminary set of tests will ensure that
        a v2 endpoint will not fail due to invalid inputs
        """
        url_route = self.url_route + "-detail"
        self.assertTrue(
            url_route,
            "APISanityTestCase expects a `url_route` to be defined")
        self.assertTrue(
            self.user,
            "APISanityTestCase expects a `self.user` to be defined")

        client = APIClient()
        client.force_authenticate(user=self.user)
        null_url = reverse(url_route, args=("null",))
        response = client.get(null_url)
        self.assertEquals(response.status_code, 404)

        url = null_url.replace("null", "1.234")
        response = client.get(url)
        self.assertEquals(response.status_code, 404)

        url = null_url.replace("null", "1.2.3.4")
        response = client.get(url)
        self.assertEquals(response.status_code, 404)

        url = reverse(url_route, args=("1234",))
        response = client.get(url)
        self.assertEquals(response.status_code, 404)

        url = reverse(url_route, args=("1-2-3-4",))
        response = client.get(url)
        self.assertEquals(response.status_code, 404)

        url = reverse(url_route, args=("beefbeefbeef",))
        response = client.get(url)
        self.assertEquals(response.status_code, 404)

        url = reverse(url_route, args=("deadbeef-dead-dead-dead-beefbeefbeef",))
        response = client.get(url)
        self.assertEquals(response.status_code, 404)
