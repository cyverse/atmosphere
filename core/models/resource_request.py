"""
resource_requests - requests to change a users resource
"""
from uuid import uuid4
from django.db import models
from django.utils import timezone
from core.models.user import AtmosphereUser
from core.models.status_type import StatusType


class ResourceRequest(models.Model):

    """
    A model to store a user's request for resourcees
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    status = models.ForeignKey(StatusType)
    request = models.TextField()
    description = models.CharField(max_length=1024, default="", blank=True)
    created_by = models.ForeignKey(AtmosphereUser)
    admin_message = models.CharField(max_length=1024, default="", blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "resource_request"
        app_label = "core"
