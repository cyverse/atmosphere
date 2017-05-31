"""
resource_requests - requests to change a users resource
"""
from django.db import models

from core.models.abstract import BaseRequest


class ResourceRequest(BaseRequest):

    """
    A model to store a user's request for resourcees
    """
    request = models.TextField()
    description = models.CharField(max_length=1024, default="", blank=True)

    class Meta:
        db_table = "resource_request"
        app_label = "core"
