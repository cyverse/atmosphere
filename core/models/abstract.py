"""
  Abstract models for atmosphere. 
  NOTE: These models should NEVER be created directly. 
  See the respective sub-classes for complete implementation details.
"""
from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.query import only_current
from core.models.group import IdentityMembership
from core.models.identity import Identity
from core.models.provider import Provider
from core.models.status_type import StatusType
from core.models.user import AtmosphereUser as User


class BaseRequest(models.Model):
    """
    Base model which represents a request object
    """
    uuid = models.CharField(max_length=36, default=uuid4)
    request = models.TextField()
    description = models.CharField(max_length=1024, default="", blank=True)
    status = models.ForeignKey(StatusType)

    # Associated creator and identity
    created_by = models.ForeignKey(User)
    membership = models.ForeignKey(IdentityMembership)

    admin_message = models.CharField(max_length=1024, default="", blank=True)

    # Request Timeline
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def is_active(cls, provider, user):
        """
        Returns whether or not the resource request is currently active for the
        given user and provider
        """
        status = StatusType.default()
        return cls.objects.filter(
            user=user, provider=provider, status=status).count() > 0



class BaseHistory(models.Model):
    """
    Base model which is used to track changes in another model
    """
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETED"

    OPERATIONS = (
        (CREATE, "The field has been created."),
        (UPDATE, "The field has been updated."),
        (DELETE, "The field has been deleted."),
    )

    field_name = models.CharField(max_length=255)
    operation = models.CharField(max_length=255,
                                 choices=OPERATIONS, default=UPDATE)
    new_value = models.TextField()
    previous_value = models.TextField()
    created_on = models.DateTimeField(default=timezone.now())

    class Meta:
        abstract = True


class InstanceSource(models.Model):
    """
    An InstanceSource can be:
    * A bootable volume 
    * A snapshot of a previous/existing Instance
    * A ProviderMachine/Application
    """
    esh = None
    provider = models.ForeignKey(Provider)
    identifier = models.CharField(max_length=256)
    created_by = models.ForeignKey(User, blank=True, null=True,
            related_name="source_set")
    created_by_identity = models.ForeignKey(Identity, blank=True, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    @classmethod
    def _current_source_query_args(cls):
        now_time = timezone.now()
        query_args = (
                #1. Provider non-end-dated
                Q(provider__end_date=None)
                | Q(provider__end_date__gt=now_time),
                #2. Source non-end-dated
                only_current(now_time),
                #3. (Seperately) Provider is active
                Q(provider__active=True))
        return query_args
    @classmethod
    def current_sources(cls):
        """
        Return a list that contains sources that match ALL criteria:
        1. NOT End dated (Or end dated later than NOW)
        2. Provider is Active
        3. Provider NOT End dated (Or end dated later than NOW)
        """
        now_time = timezone.now()
        return InstanceSource.objects.filter(
                *InstanceSource._current_source_query_args())
        #return InstanceSource.objects.filter(
        #    Q(provider__end_date=None)
        #    | Q(provider__end_date__gt=now_time),
        #    only_current(now_time), provider__active=True)

    #Useful for querying/decision making w/o a Try/Except
    def is_volume(self):
        try:
            volume = self.volume
            return True
        except Exception, not_volume:
            return False

    def is_machine(self):
        try:
            machine = self.providermachine
            return True
        except Exception, not_machine:
            return False

    #Useful for the admin fields
    def source_end_date(self):
        raise NotImplementedError("Implement this in the sub-class")
    def source_provider(self):
        raise NotImplementedError("Implement this in the sub-class")
    def source_identifier(self):
        raise NotImplementedError("Implement this in the sub-class")
    class Meta:
        db_table = "instance_source"
        app_label = "core"
        unique_together = ('provider', 'identifier')
