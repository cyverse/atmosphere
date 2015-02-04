"""
requests  - tracks requests
"""
from core.models.abstract import BaseRequest


class AllocationRequest(BaseRequest):
    """
    Tracks requests made by users to change their current Allocation
    """
    class Meta:
        db_table = "allocation_request"
        app_label = "core"


class QuotaRequest(BaseRequest):
    """
    Tracks requests made by users to change their current Quota
    """
    class Meta:
        db_table = "quota_request"
        app_label = "core"
