"""
test resource requests models
"""
from django.test import TestCase

from core.models import ResourceRequest, StatusType


class TestResouceRequest(TestCase):

    def setUp(self):
        self.status = StatusType.objects.get(name="pending")
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
