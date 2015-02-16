from django.db import models
from django.db.models import Q
from django.utils import timezone

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
    * A ProviderMachine/Application
    """
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

    @property
    def current_source(self):
        source = getattr(self, "volume", getattr(self, "providermachine", None))
        if not source:
            raise SourceNotFound("A source could not be found for %s." % self)
        return source

    def is_volume(self):
        try:
            self.volume
        except NameError:
            return False
        else:            
            return True

    def is_machine(self):
        try:
            self.providermachine
        except NameError:
            return False
        else:
            return True

    class Meta:
        db_table = "instance_source"
        app_label = "core"
        unique_together = ('provider', 'identifier')
