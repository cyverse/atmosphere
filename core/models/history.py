"""
history - Track changes made to model instances
"""
from django.db import models

from core.models.abstract import BaseHistory


class QuotaHistory(BaseHistory):
    """
    Tracks changes made to a Quota
    """
    quota = models.ForeignKey("Quota", related_name="history")

    class Meta:
        db_table = "quota_history"
        app_label = "core"
