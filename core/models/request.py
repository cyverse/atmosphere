"""
requests  - tracks requests
"""
from django.db import models

from core.models.abstract import BaseRequest


class AllocationRequest(BaseRequest):
    """
    Tracks requests made by users to change their current Allocation
    """
    request = models.TextField()
    description = models.CharField(max_length=1024, default="", blank=True)

    class Meta:
        db_table = "allocation_request"
        app_label = "core"


class QuotaRequest(BaseRequest):
    """
    Tracks requests made by users to change their current Quota
    """
    request = models.TextField()
    description = models.CharField(max_length=1024, default="", blank=True)

    class Meta:
        db_table = "quota_request"
        app_label = "core"
