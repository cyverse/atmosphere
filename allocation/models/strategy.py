"""
Allocation Strategy represented as a Purely-Python object
"""
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from allocation.models import \
    AllocationRecharge, IgnoreStatusRule, MultiplySizeCPU,\
    Allocation, TimeUnit
from allocation.models import Instance as AllocInstance

from threepio import logger

class PythonAllocationStrategy(object):

    """
    PythonAllocationStrategy is powered by CORE: Identity, Allocation
    Start date and End date REQUIRED
    Interval *may* be removed in a future release..

    To be implemented:
    * Refresh Behavior
    * Counting Behavior
    * Rules Behavior
    * ???
    """

    def __init__(self, counting_behavior,
                 recharge_behaviors=[], rule_behaviors=[]):
        self.counting_behavior = counting_behavior
        self.recharge_behaviors = recharge_behaviors
        self.rule_behaviors = rule_behaviors

    def get_instance_list(self, identity, limit_instances=[], limit_history=[]):
        from service.monitoring import _core_instances_for
        # Retrieve the core that could have an impact..
        core_instances = _core_instances_for(
            identity,
            self.counting_behavior.start_date)
        # Convert Core Models --> Allocation/core Models
        alloc_instances = []
        for inst in core_instances:
            if limit_instances and inst.provider_alias not in limit_instances:
                continue
            try:
                allocation_instance = AllocInstance.from_core(
                        inst,
                        self.counting_behavior.start_date,
                        limit_history=limit_history
                    )
                if allocation_instance:
                    alloc_instances.append(allocation_instance)
            except Exception as exc:
                logger.exception("Instance %s could not be counted: %s" % (inst, exc))
        return alloc_instances

    def apply(self, identity, core_allocation, limit_instances=[], limit_history=[]):
        instances = self.get_instance_list(
            identity,
            limit_instances=limit_instances,
            limit_history=limit_history)

        credits = []
        for behavior in self.recharge_behaviors:
            if core_allocation:
                credits.extend(
                    behavior.get_allocation_credits(
                        unit=TimeUnit.minute,
                        amount=core_allocation.threshold))
            else:
                # Unlimited for 'no allocation'
                credits.extend(
                    behavior.get_allocation_credits(
                        unit=TimeUnit.infinite,
                        amount=1))

        rules = []
        for behavior in self.rule_behaviors:
            rules.extend(
                behavior.apply_rules(identity, core_allocation)
            )

        return Allocation(
            credits=credits, rules=rules,
            instances=instances,
            start_date=self.counting_behavior.start_date,
            end_date=self.counting_behavior.end_date,
            interval_delta=self.counting_behavior.interval_delta)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "Counting Behavior: %s, Refresh:%s Rules:%s "\
            % (self.counting_behavior, self.recharge_behaviors,
               self.rule_behaviors)


class PythonRulesBehavior(object):

    """
    The Rules Behavior
    All 'PythonRulesBehavior' objects define a set of rules to be applied
    When/How the rules are applied is dependent on the behavior
    """

    def __init__(self, rules=[]):
        self.rules = rules

    def apply_rules(self, identity, core_allocation):
        """
        Logic used to apply rules goes here.
        """
        raise NotImplementedError("To be applied by the implementing class")
    pass


class GlobalRules(PythonRulesBehavior):

    """
    The Global Rules behavior will ALWAYS apply
    """

    def apply_rules(self, identity, core_application):
        return self.rules


class NewUserRules(PythonRulesBehavior):

    """
    The StaffRules behavior will only apply if the identity is aenoted as staff
    """

    def __init__(self, rules, cutoff_date):
        super(NewUserRules, self).__init__(rules)
        self.cutoff_date = cutoff_date

    def apply_rules(self, identity, core_application):
        if identity.created_by.date_joined > self.cutoff_date:
            return self.rules
        return []


class StaffRules(PythonRulesBehavior):

    """
    The StaffRules behavior will only apply if the identity is denoted as staff
    """

    def apply_rules(self, identity, core_application):
        if identity.created_by.is_staff:
            return self.rules
        return []


class MultiplySizeCPURule(GlobalRules):

    def __init__(self, rules=[]):
        multiply_by_cpu = MultiplySizeCPU(
            name="Multiply TimeUsed by CPU",
            multiplier=1)
        super(MultiplySizeCPURule, self).__init__([multiply_by_cpu])


class IgnoreNonActiveStatus(GlobalRules):

    def __init__(self, rules=[]):
        ignore_inactive = IgnoreStatusRule(
            "Ignore Inactive StatusHistory",
            value=["build", "pending",
                   "networking", "deploying",
                   "hard_reboot", "reboot",
                   "migrating", "rescue",
                   "resize", "verify_resize",
                   "shutoff", "shutting-down",
                   "suspended", "terminated",
                   "deleted", "deploy_error", "error", "Unknown", "unknown", "N/A",
                   ])
        super(IgnoreNonActiveStatus, self).__init__([ignore_inactive])


class PythonRefreshBehavior(object):

    """
    Define a set of rules that explain when/how a user should be refreshed.
    IF: start_increase = 1/1/2015, end_increase = 1/31/2015
        AND interval_delta=3600
    Credits: [1/hr*24hr/day*31 days == 744 credits]
    """
    start_increase = None
    interval_delta = None
    end_increase = None

    def __init__(self, start_increase, end_increase, interval_delta):
        raise NotImplementedError(
            "Cannot be directly instantiated. "
            "Use a subclass of CountingBehavior to continue.")

    def set_dates(self, start_increase, end_increase, interval_delta):
        """
        Use this method to instantiate the dates on a PythonRefreshBehavior
        """
        self.start_increase = start_increase
        self.end_increase = end_increase
        self.interval_delta = interval_delta

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        print_str = "Refresh On %s." % self.start_increase
        if self.interval_delta:
            print_str += " New Refresh every %s." % self.interval_delta
        if self.end_increase:
            print_str += " Stop Refresh On/Before %s." % self.start_increase
        return print_str

    def get_allocation_credits(self, unit, amount):
        """
        Returns a list of Credits from 1 < n
        Amount of credits determinant on 'end_increase' and 'interval_delta'
        Unit and Amount expected to create the Recharge
        """
        recharge_date = self.start_increase

        if self.end_increase:
            stop_refresh = self.end_increase
        elif self.interval_delta:
            stop_refresh = timezone.now()
        else:
            stop_refresh = self.start_increase

        credits_list = []
        while recharge_date <= stop_refresh:
            credits_list.append(
                AllocationRecharge(
                    name="Increase by %s %s" % (amount, unit),
                    unit=unit,
                    amount=amount,
                    recharge_date=recharge_date)
            )
            if not self.interval_delta:
                break
            recharge_date = recharge_date + self.interval_delta
        return credits_list

    def _get_next_value(self, next_value):
        raise NotImplementedError("Implement _get_next_value")


class OneTimeRefresh(PythonRefreshBehavior):

    """
    A One Time Refresh is granted ONCE on the start date,
    It has no End date and no Interval
    """

    def __init__(self, start_increase):
        self.set_dates(start_increase, None, None)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return super(OneTimeRefresh, self).__unicode__()


class RecurringRefresh(PythonRefreshBehavior):

    """
      Accepts:
      A time to Start refreshing,
      A RELATIVE delta or TIME delta that
      represents when to grant the NEXT refresh
      A time to Stop refreshing
    """

    def __init__(self, start_increase, end_increase, interval_delta):
        self.set_dates(start_increase, end_increase, interval_delta)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return super(RecurringRefresh, self).__unicode__()


class PythonCountingBehavior(object):
    start_date = None
    end_date = None
    interval_delta = None

    @classmethod
    def _validate(cls, start_date, end_date, interval_delta):
        if not start_date:
            start_date = timezone.now()
        if not end_date:
            end_date = timezone.now()
        if interval_delta and\
                not isinstance(interval_delta,
                               (timezone.timedelta, relativedelta)):
            raise TypeError("window_delta REQUIRES a timedelta/relativedelta")
        if end_date < start_date:
            raise ValueError("End date (%s) is GREATER than start date (%s)"
                             % (end_date, start_date))
        return (start_date, end_date, interval_delta)

    def __init__(self, start_date, end_date):
        """
        Counting Behaviors themselves cannot be instantiated,
        they must be subclassed.
        """
        raise NotImplementedError(
            "Cannot be directly instantiated. "
            "Use a subclass of PythonCountingBehavior to continue.")

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        next_start = self.start_date

        print_list = []
        while next_start <= self.end_date:
            # Set the 'end' based on interval or end date
            if self.interval_delta:
                next_stop = next_start + self.interval_delta
            else:
                next_stop = self.end_date
            # If next_stop is at/ahead of the end date,
            # Stop at the end date
            if next_stop >= self.end_date:
                next_stop = self.end_date
            print_str = "Count from %s to %s"\
                        % (next_start, next_stop)
            print_list.append(
                print_str
            )
            # BASE CASE - We are ahead of 'end date' STOP!
            if next_stop >= self.end_date:
                break
            next_start = next_stop
        # Guaranteed >1 element in print_list
        return "\n".join(print_list)

    def set_dates(self, start_date, end_date, interval_delta=None):
        PythonCountingBehavior._validate(start_date, end_date, interval_delta)
        self.start_date = start_date
        self.end_date = end_date
        self.interval_delta = interval_delta


class FixedWindow(PythonCountingBehavior):

    """
    A fixed window gives complete control over how to 'Count time'
    window_start - When to begin counting time
    window_end - When to stop counting time
    interval_delta - Split ALL time up between 'window_start' and 'window_end'
    """

    def __init__(self, window_start, window_end, interval_delta=None):
        self.set_dates(window_start, window_end, interval_delta)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return super(FixedWindow, self).__unicode__()


class FixedStartSlidingWindow(PythonCountingBehavior):

    """
    window_delta - can be RELATIVEdelta or TIMEdelta
    """
    window_start = None
    window_delta = None

    @classmethod
    def _validate(cls, window_start, window_delta, interval_delta=None):
        if not window_start:
            window_start = timezone.now()
        if not window_delta or \
                not isinstance(window_delta,
                               (timezone.timedelta, relativedelta)):
            raise Exception("window_delta REQUIRES a timedelta/relativedelta")

        start_date = window_start
        end_date = window_start + window_delta
        return (start_date, end_date, interval_delta)

    def __init__(self, window_start, window_delta, interval_delta=None):
        (start_date, end_date, interval_delta) =\
            FixedStartSlidingWindow._validate(
                window_start, window_delta)
        self.set_dates(start_date, end_date, interval_delta)
        self.window_delta = window_delta

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        original_str = super(FixedStartSlidingWindow, self).__unicode__()
        return "%s (Fixed Start. Window size: %s)"\
            % (original_str, self.window_delta)


class FixedEndSlidingWindow(PythonCountingBehavior):

    """
    The 'delta' can be RELATIVEdelta or TIMEdelta
    """
    window_end = None
    window_delta = None

    @classmethod
    def _validate(cls, window_end, window_delta, interval_delta=None):
        if not window_end:
            window_end = timezone.now()
        if not window_delta or \
                not isinstance(window_delta,
                               (timezone.timedelta, relativedelta)):
            raise Exception("window_delta REQUIRES a timedelta/relativedelta")

        start_date = window_end - window_delta
        end_date = window_end
        return (start_date, end_date, interval_delta)

    def __init__(self, window_end, window_delta, interval_delta=None):
        (start_date, end_date, interval_delta) =\
            FixedEndSlidingWindow._validate(
            window_end, window_delta, interval_delta)
        self.set_dates(start_date, end_date, interval_delta)
        self.window_delta = window_delta

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        original_str = super(FixedEndSlidingWindow, self).__unicode__()
        return "%s (Fixed End. Window size: %s)"\
            % (original_str, self.window_delta)
