"""
  Abstract models for atmosphere.
  NOTE: These models should NEVER be created directly.
  See the respective sub-classes for complete implementation details.
"""
from uuid import uuid4
from django.db import models
from django.utils import timezone

from core.exceptions import InvalidMembership, ProviderLimitExceeded
from core.models.instance_source import InstanceSource
from core.models.status_type import StatusType
from core.models.user import AtmosphereUser as User

UNRESOLVED_STATES = ["pending", "failed"]


class BaseRequest(models.Model):
    """
    Base model which represents a request object
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    status = models.ForeignKey(StatusType)

    # Associated creator and identity
    created_by = models.ForeignKey(User)
    membership = models.ForeignKey("IdentityMembership")

    admin_message = models.CharField(max_length=1024, default="", blank=True)

    # Request Timeline
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return "%s: %s - %s" %\
            (self.uuid, self.status, self.created_by)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Only allow one active request per provider
        """
        if not self.pk and self.is_active(self.membership):
            # temporary workaround to exclude ResourceRequests from the ProviderLimitExceeded check
            if "ResourceRequest" in str(type(self)
                                       ):    # THIS IS A HACK REMOVE THIS
                super(BaseRequest, self).save(*args, **kwargs)
                return
            raise ProviderLimitExceeded(
                "The number of open requests has been exceeded."
            )

        if not self.membership.is_member(self.created_by):
            raise InvalidMembership(
                "This membership does not belong to the user"
            )

        super(BaseRequest, self).save(*args, **kwargs)

    @classmethod
    def is_active(cls, identity_membership):
        """
        Return if a request is active for the identity_membership
        """
        return cls.objects.filter(
            membership=identity_membership, status__name__in=UNRESOLVED_STATES
        ).count() > 0

    def is_closed(self):
        return self.status.name not in UNRESOLVED_STATES

    def is_approved(self):
        return self.status.name == "approved"

    def is_denied(self):
        return self.status.name == "denied"

    def can_modify(self, user):
        """
        Returns whether the user can modify the request
        """
        # Only pending requests can be modified by the owner
        if self.created_by.username == user.username:
            return self.status.name == "pending"

        return user.is_staff or user.is_superuser


class BaseSource(models.Model):
    """
    Source object which can be booted
    """
    instance_source = models.OneToOneField(InstanceSource)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Save the instance_source then the model
        """
        self.instance_source.save()
        super(BaseSource, self).save(*args, **kwargs)

    @property
    def start_date(self):
        return self.instance_source.start_date

    @property
    def end_date(self):
        return self.instance_source.end_date

    @end_date.setter
    def end_date(self, value):
        self.instance_source.end_date = value

    @property
    def provider(self):
        return self.instance_source.provider

    @property
    def identifier(self):
        return self.instance_source.identifier

    def to_dict(self):
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "identifier": self.identifier,
            "provider_uuid": self.provider.uuid
        }


class SingletonModel(models.Model):
    """
    A model that will ensure at-most-one row exists in the database
    """

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_instance(cls):
        try:
            return cls.objects.get(pk=1)
        except cls.DoesNotExist:
            return cls()

    class Meta:
        abstract = True
