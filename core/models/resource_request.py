"""
resource_requests - requests to change a users resource
"""
from django.db import models

from core.models.abstract import BaseRequest


class ResourceRequest(BaseRequest):

    """
    Tracks users requests to change their current Resources
    """
    request = models.TextField()
    description = models.CharField(max_length=1024, default="", blank=True)
    allocation = models.ForeignKey("Allocation", null=True)
    quota = models.ForeignKey("Quota", null=True)

    class Meta:
        db_table = "resource_request"
        app_label = "core"
