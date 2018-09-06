"""
test resource requests models
"""
from django.test import TestCase

from core.models import ResourceRequest
from core.models.status_type import get_status_type


class TestResouceRequest(TestCase):

    def setUp(self):
        self.status = get_status_type()
        self.message = "Resource admin message"
        self.request = "Resource of size x"
        self.blank_request = ResourceRequest(
            admin_message=self.message, request=self.request,
            status=self.status)

    def test_blank_request(self):
        self.assertEquals(self.blank_request.admin_message, self.message)
        self.assertEquals(self.blank_request.status, self.status)
        self.assertEquals(
            self.blank_request.request, self.request)
