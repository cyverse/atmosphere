import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from core.exceptions import SourceNotFound
from core.query import only_current
from core.models.identity import Identity
from core.models.provider import Provider
from core.models.user import AtmosphereUser as User


class InstanceSource(models.Model):
    """
    An InstanceSource can be:
    * A bootable volume
    * A snapshot of a previous/existing Instance
    * A ProviderMachine
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    provider = models.ForeignKey(Provider)
    identifier = models.CharField(max_length=256)
    created_by = models.ForeignKey(User, blank=True, null=True,
                                   related_name="source_set")
    created_by_identity = models.ForeignKey(Identity, blank=True, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return "%s Provider:%s Created_by:%s" % (
            self.identifier, self.provider, self.created_by)

    @classmethod
    def _current_source_query_args(cls):
        now_time = timezone.now()
        query_args = (
            # 1. Provider non-end-dated
            Q(provider__end_date=None)
            | Q(provider__end_date__gt=now_time),
            # 2. Source non-end-dated
            only_current(now_time),
            # 3. (Seperately) Provider is active
            Q(provider__active=True))
        return query_args

    @classmethod
    def get_source(cls, source_alias, queryset=None):
        """
        Given the UUID, retrieve the source object.
        """
        if not queryset:
            queryset = cls.current_sources()
        try:
            return queryset.get(identifier=source_alias)
        except MultipleObjectsReturned:
            raise Exception(
                "Multiple sources use the identifier '%s' -- "
                "pass a refined queryset to select the appropriate source"
                % source_alias)
        except ObjectDoesNotExist:
            return None

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

    @property
    def current_source(self):
        source = getattr(
            self,
            "volume",
            getattr(
                self,
                "providermachine",
                None))
        if not source:
            raise SourceNotFound("A source could not be found for %s." % self)
        return source

    @property
    def source_type(self):
        if self.is_machine():
            return "machine"
        elif self.is_volume():
            return "volume"
        elif self.is_snapshot():
            return "snapshot"

    def is_snapshot(self):
        """
        Coming soon!
        """
        try:
            self.volume
        except ObjectDoesNotExist:
            return False
        except AttributeError:
            # TODO: Remove this case when we add to core.
            return False
        else:
            return True

    def is_volume(self):
        try:
            self.volume
        except ObjectDoesNotExist:
            return False
        except NameError:
            return False
        else:
            return True

    def is_machine(self):
        try:
            self.providermachine
        except ObjectDoesNotExist:
            return False
        except NameError:
            return False
        else:
            return True

    def is_owner(self, atmo_user):
        return (self.created_by == atmo_user |
                self.application.created_by == atmo_user)

    def change_owner(self, identity, user=None):
        if not user:
            user = identity.created_by

        self.created_by = user
        self.created_by_identity = identity
        self.save()

    class Meta:
        db_table = "instance_source"
        app_label = "core"
        unique_together = ('provider', 'identifier')
