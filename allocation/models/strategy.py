from dateutil.relativedelta import relativedelta

from django.utils import timezone

# Imports Atmosphere Specific Settings
from django.conf import settings

from allocation.models import \
    AllocationRecharge, AllocationUnlimited,\
    IgnoreStatusRule, MultiplySizeCPU,\
    Allocation, TimeUnit
from allocation.models import Instance as AllocInstance
from service.monitoring import _core_instances_for, get_delta


class AllocationStrategy(object):
    """
    AllocationStrategy is powered by CORE: Identity, Allocation
    Start date and End date REQUIRED
    Interval *may* be removed in a future release..

    To be implemented:
    * Refresh Behavior
    * Counting Behavior
    * Rules Behavior
    * ???
    """
    def __init__(self, identity, core_allocation,
                 start_date, end_date, interval_delta=None):
        self.identity = identity
        self.allocation = core_allocation
        # Guaranteed a range
        # NOTE:IF BOTH are NONE: Starting @ FIXED_WINDOW until NOW
        self.counting_behavior(start_date, end_date, interval_delta)

        instances = self.get_instance_list()
        credits = self.recharge_behavior()
        rules = self.rules_behavior()

        self.allocation = Allocation(
            credits=credits, rules=rules,
            instances=instances,
            start_date=self.start_date, end_date=self.end_date,
            interval_delta=self.interval_delta)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "Strategy Result:%s " % self.allocation

    def counting_behavior(self, start_date, end_date, interval_delta):
        if not end_date:
            end_date = timezone.now()

        if not start_date:
            delta_time = get_delta(self.core_allocation,
                                   settings.FIXED_WINDOW, end_date)
            start_date = end_date - delta_time
        elif not interval_delta:
            delta_time = end_date - start_date
        else:
            delta_time = interval_delta

        self.start_date = start_date
        self.end_date = end_date
        self.interval_delta = delta_time

    def get_instance_list(self):
        # Retrieve the core that could have an impact..
        core_instances = _core_instances_for(self.identity, self.start_date)
        # Convert Core Models --> Allocation/core Models
        alloc_instances = [AllocInstance.from_core(inst, self.start_date)
                           for inst in core_instances]
        return alloc_instances

    def recharge_behavior(self):
        raise NotImplementedError("No Free Lunch")

    def rules_behavior(self):
        raise NotImplementedError("No Free Lunch")


class MonthlyAllocation(AllocationStrategy):
    """
    The 'MonthlyAllocation' strategy takes Core Identity and Allocation objects
    The GOAL is to maintain functionality parity
    to that of the ORIGINAL allocation system.
    """

    def recharge_behavior(self):
        if self.core_allocation:
            initial_credit = AllocationRecharge(
                name="%s Assigned allocation"
                     % self.identity.created_by.username,
                unit=TimeUnit.minute, amount=self.core_allocation.threshold,
                recharge_date=self.start_date)
        else:
            initial_credit = AllocationUnlimited(self.start_date)
        return [initial_credit]

    def rules_behavior(self):
        multiply_by_cpu = MultiplySizeCPU(
            name="Multiply TimeUsed by CPU",
            multiplier=1)
        # Noteably MISSING: 'active', 'running'
        ignore_inactive = IgnoreStatusRule(
            "Ignore Inactive StatusHistory",
            value=["build", "pending",
                   "hard_reboot", "reboot",
                   "migrating", "rescue",
                   "resize", "verify_resize",
                   "shutoff", "shutting-down",
                   "suspended", "terminated",
                   "deleted", "error", "unknown", "N/A",
                   ])
        return [multiply_by_cpu, ignore_inactive]


class RefreshBehavior(object):
    """
    Define a set of rules that explain when/how a user should be refreshed.
    IF: start_date = 1/1/2015, end_date = 1/31/2015 AND seconds=3600
    Credits == [1/hr*24hr/day*31 days == 744 credits]
    """
    start_date = None
    end_date = None
    credit_amount = None

    def __init__(self, start_date, end_date, credit_seconds):
        self.start_date = start_date
        self.end_date = end_date
        self.credit_seconds = credit_seconds

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "Grant Credit every %s seconds. Start on %s, End on %s"\
            % (self.credit_seconds, self.start_date, self.end_date)

    def generate_credits(self):
        next_value = self._get_next_value(self.start_date)
        end_at = self.end_date
        credits_list = []
        while next_value < end_at:
            credits_list.append(
                AllocationRecharge(
                    name="Increase by %s seconds" % self.credit_seconds,
                    unit=TimeUnit.second,
                    amount=self.credit_seconds,
                    recharge_date=next_value)
                )
            new_next = self._get_next_value(next_value)
            if new_next == next_value:
                raise Exception("Infinite loop detected!")
            next_value = new_next
        return credits_list

    def _get_next_value(self, next_value):
        raise NotImplementedError("Implement _get_next_value")


class OneTimeRefresh(RefreshBehavior):
    """
      Accepts:
      datetime time stamp
      AND
      Credit Amount (In seconds)
    """

    def __init__(self, start_date, end_date, credit_seconds, timestamp):
        super(OneTimeRefresh, self).__init__(
            start_date, end_date, credit_seconds)
        self.timestamp = timestamp

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return super(OneTimeRefresh, self).__unicode__()

    def _get_next_value(self, next_value):
        return self.timestamp


class IntervalRefresh(RefreshBehavior):
    """
      Accepts:
      RELATIVE delta or TIME delta
      AND
      Credit Amount (In seconds)
    """
    def __init__(self, start_date, end_date, credit_seconds, interval_date):
        super(IntervalRefresh, self).__init__(
            start_date, end_date, credit_seconds)
        self.interval = interval_date

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return super(IntervalRefresh, self).__unicode__()

    def _get_next_value(self, next_value):
        return next_value + self.interval


class CountingBehavior(object):
    start_date = None
    end_date = None

    @classmethod
    def _validate(cls, start_date, end_date):
        if not start_date:
            start_date = timezone.now()
        if not end_date:
            end_date = timezone.now()
        if end_date < start_date:
            raise ValueError("End date (%s) is GREATER than start date (%s)"
                             % (end_date, start_date))
        return (start_date, end_date)

    def __init__(self, start_date, end_date):
        """
        Counting Behaviors themselves cannot be instantiated,
        they must be subclassed.
        """
        raise NotImplementedError(
            "Cannot be directly instantiated. "
            "Use a subclass of CountingBehavior to continue.")

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "Count from %s to %s"\
            % (self.start_date, self.end_date)

    def set_dates(self, start_date, end_date):
        CountingBehavior._validate(start_date, end_date)
        self.start_date = start_date
        self.end_date = end_date


class FixedWindow(CountingBehavior):
    """
    """
    window_start = None
    window_end = None

    def __init__(self, window_start, window_end):
        self.set_dates(window_start, window_end)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return super(FixedWindow, self).__unicode__()


class FixedStartSlidingWindow(CountingBehavior):
    """
    The 'delta' can be RELATIVEdelta or TIMEdelta
    """
    window_start = None
    window_delta = None

    @classmethod
    def _validate(cls, window_start, window_delta):
        if not window_start:
            window_start = timezone.now()
        if not window_delta or \
                not isinstance(window_delta,
                               (timezone.timedelta, relativedelta)):
            raise Exception("window_delta REQUIRES a timedelta/relativedelta")

        start_date = window_start
        end_date = window_start + window_delta
        return (start_date, end_date)

    def __init__(self, window_start, window_delta):
        start_date, end_date = FixedStartSlidingWindow._validate(
            window_start, window_delta)
        self.set_dates(start_date, end_date)
        self.window_delta = window_delta

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        original_str = super(FixedStartSlidingWindow, self).__unicode__()
        return "%s (Fixed Start. Window size: %s)"\
            % (original_str, self.window_delta)


class FixedEndSlidingWindow(CountingBehavior):
    """
    The 'delta' can be RELATIVEdelta or TIMEdelta
    """
    window_end = None
    window_delta = None

    @classmethod
    def _validate(cls, window_end, window_delta):
        if not window_end:
            window_end = timezone.now()
        if not window_delta or \
                not isinstance(window_delta,
                               (timezone.timedelta, relativedelta)):
            raise Exception("window_delta REQUIRES a timedelta/relativedelta")
        start_date = window_end - window_delta
        end_date = window_end
        return (start_date, end_date)

    def __init__(self, window_end, window_delta):
        start_date, end_date = FixedEndSlidingWindow._validate(
            window_end, window_delta)
        self.set_dates(start_date, end_date)
        self.window_delta = window_delta

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        original_str = super(FixedEndSlidingWindow, self).__unicode__()
        return "%s (Fixed End. Window size: %s)"\
            % (original_str, self.window_delta)
