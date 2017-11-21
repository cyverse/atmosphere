"""
    InstanceAccess model for atmosphere.
"""

import uuid

from django.db import models
from django.db.models import Q
from core.models.status_type import StatusType


class InstanceAccess(models.Model):
    """
    InstanceAccess:
     - Instance: Location to grant user-access
     - User: to be granted access to the instance
     - StatusType: Can be 'pending', 'approved', 'rejected'
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    instance = models.ForeignKey("Instance", related_name="access_list")
    user = models.ForeignKey("AtmosphereUser", related_name="instance_access")
    status = models.ForeignKey(StatusType)
    updated = models.DateTimeField(auto_now=True)

    @staticmethod
    def shared_with_user(username):
        """
        Return all InstanceAccess entries for the user
        - All instances the user has created
        - All instances the user has an InstanceAccess entry for
        """
        return InstanceAccess.objects.filter(
            Q(user__username=username) |
            Q(instance__created_by__username=username)
        )

    def remove_access(self):
        from core.events.serializers.instance_access import RemoveInstanceAccessSerializer
        serializer = RemoveInstanceAccessSerializer(data={
            'user': self.user.username,
            'instance': self.instance.provider_alias
        })
        if not serializer.is_valid():
            errors = serializer.errors
            if 'not in the instance access list':
                return serializer
            raise Exception(
                "Error occurred while removing instance_access for "
                "Instance:%s, Username:%s -- %s"
                % (
                    self.instance,
                    self.user,
                    errors))
        serializer.save()
        return serializer

    def add_access(self):
        from core.events.serializers.instance_access import AddInstanceAccessSerializer
        serializer = AddInstanceAccessSerializer(data={
            'user': self.user.username,
            'instance': self.instance.provider_alias
        })
        if not serializer.is_valid():
            errors = serializer.errors
            if 'already in the instance access list':
                return serializer
            raise Exception(
                "Error occurred while adding self for "
                "Instance:%s, User:%s -- %s"
                % (
                    self.instance,
                    self.user,
                    errors))
        serializer.save()
        return serializer

    def __unicode__(self):
        return "Request(%s) for User:%s to access Instance:%s" %\
                (self.status.name, self.user, self.instance)
