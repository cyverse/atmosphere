"""
Strategy (implemented as Django DB based models)
"""
from dateutil.relativedelta import relativedelta

from uuid import uuid4
from django.db import models
from django.utils import timezone

from allocation.models.strategy import \
    PythonAllocationStrategy, OneTimeRefresh, FixedWindow,\
    IgnoreNonActiveStatus, MultiplySizeCPURule

# NOTE: Carried over from OLD allocation model. This will be changing soon


class Allocation(models.Model):

    """
    Allocation limits the amount of time resources that can be used for
    a User/Group. Allocations are set at the Identity Level
    in IdentityMembership.
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    # One week
    threshold = models.IntegerField(null=True,
                                    blank=True,
                                    default=7 * 24 * 60)  # In Minutes
    # Over One year
    delta = models.IntegerField(null=True,
                                blank=True,
                                default=365 * 24 * 60)  # In Minutes

    def __unicode__(self):
        return "Threshold: %s minutes over Delta: %s minutes" %\
            (self.threshold, self.delta)

    @classmethod
    def default_allocation(self, provider=None):
        """
        TODO: Refactor so that a provider can define NEW default allocations,
        rather than hard-coded
        """
        return Allocation.objects.get_or_create(
            **Allocation.default_dict())[0]

    @classmethod
    def default_dict(self):
        return {
            'threshold': self._meta.get_field('threshold').default,
            'delta': self._meta.get_field('delta').default
        }

    class Meta:
        db_table = 'allocation'
        app_label = 'core'
        unique_together = ("threshold", "delta")


class RulesBehavior(models.Model):

    """
    allow real-time modification of the rules used on the allocation engine.
    """
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = "rules_behavior"
        app_label = "core"


class RefreshBehavior(models.Model):

    """
    real-time modification of how to refresh a users allocation.
    """

    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = "refresh_behavior"
        app_label = "core"


class CountingBehavior(models.Model):

    """
    Should be used as part of assigning another class that references
    CountingBehavior, but could be used as an 'emergency catch' for
    String evaluation to take specific action in-code.
    """
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = "counting_behavior"
        app_label = "core"


class AllocationStrategy(models.Model):

    """
    AllocationStrategy is composed of three types of strategy:
        * Counting Strategy -- one-to-one
        * Refresh Strategies -- one-to-many
        * Rules Strategies -- one-to-many
    AllocationStrategy's have one-to-one mapping to provider
    """
    provider = models.OneToOneField("Provider", unique=True)
    counting_behavior = models.ForeignKey(CountingBehavior)
    refresh_behaviors = models.ManyToManyField(
        RefreshBehavior, blank=True)
    rules_behaviors = models.ManyToManyField(
        RulesBehavior, blank=True)

    def _parse_counting_behavior(self, identity, now=None):
        if not now:
            now = timezone.now()
        try:
            cb = self.counting_behavior
            if cb.name == "1 Month - Calendar Window":
                return self._first_of_month_window(now)
            elif cb.name == "1 Month - Calendar Window - Anniversary":
                return self._anniversary_window(identity, now)
        except CountingBehavior.DoesNotExist:
            return self._first_of_month_window(now)

    def _anniversary_window(self, identity, now=None):
        if not now:
            now = timezone.now()
        user_join = identity.created_by.date_joined
        one_month = relativedelta(months=1)
        monthiversary = timezone.datetime(
            now.year, now.month, user_join.day, tzinfo=timezone.utc)
        start_month = monthiversary \
            if user_join.day > now.day \
            else monthiversary - one_month
        if user_join.day > now.day:
            start_month = monthiversary
        else:
            start_month = monthiversary - one_month
        next_month = start_month + one_month
        return FixedWindow(start_month, next_month)

    def _first_of_month_window(self, now=None):
        if not now:
            now = timezone.now()
        first_month = timezone.datetime(now.year, now.month, 1,
                                        tzinfo=timezone.utc)
        next_month = first_month + relativedelta(months=1)
        return FixedWindow(first_month, now)

    def _parse_rules_behaviors(self):
        rule_behaviors = []
        for rb in self.rules_behaviors.all():
            if rb.name == "Ignore non-active status":
                rule_behaviors.append(IgnoreNonActiveStatus())
            elif rb.name == "Multiply by Size CPU":
                rule_behaviors.append(MultiplySizeCPURule())
            else:
                continue
        return rule_behaviors

    def _parse_refresh_behaviors(self, identity, now=None):
        if not now:
            now = timezone.now()
        refresh_behaviors = []
        for rb in self.refresh_behaviors.all():
            if rb.name == "First of the Month":
                refresh_behaviors.append(
                    self._first_of_month_refresh(now))
            elif rb.name == "Anniversary Date":
                refresh_behaviors.append(
                    self._anniversary_month_refresh(identity, now))
            else:
                continue
        return refresh_behaviors

    def _anniversary_month_refresh(self, identity, now=None):
        if not now:
            now = timezone.now()
        one_month = relativedelta(months=1)
        user_join = identity.created_by.date_joined
        monthiversary = timezone.datetime(
            now.year, now.month, user_join.day,
            tzinfo=timezone.utc)
        increase_date = monthiversary \
            if user_join.day > now.day \
            else monthiversary - one_month
        return OneTimeRefresh(increase_date)

    def _first_of_month_refresh(self, now=None):
        if not now:
            now = timezone.now()
        increase_date = timezone.datetime(now.year, now.month, 1,
                                          tzinfo=timezone.utc)
        return OneTimeRefresh(increase_date)

    def apply(self, identity, core_allocation):
        """
        Create an allocation.models.allocationstrategy
        """
        now = timezone.now()
        counting_behavior = self._parse_counting_behavior(identity, now)
        refresh_behaviors = self._parse_refresh_behaviors(identity, now)
        rules_behaviors = self._parse_rules_behaviors()
        new_strategy = PythonAllocationStrategy(
            counting_behavior, refresh_behaviors, rules_behaviors)
        return new_strategy.apply(identity, core_allocation)

    def execute(self, identity, core_allocation):
        from allocation.engine import calculate_allocation
        allocation_input = self.apply(identity, core_allocation)
        return calculate_allocation(allocation_input)

    def __unicode__(self):
        return "Provider:%s Counting:%s Refresh:%s Rules:%s"\
            % (self.provider, self.counting_behavior,
               self.refresh_behaviors.all(), self.rules_behaviors.all())

    class Meta:
        db_table = "allocation_strategy"
        app_label = "core"
