"""
Core-representation (Not-complete models) required for allocation

TODO: 'Duck-Type' to pull all required attributes from a
      core.models.[Instance,Provider,Machine,Size]
      To make initializing these models 100x easier!
"""
import calendar
import pytz

import warlock

from django.db.models import Q
from django.utils.timezone import timedelta, datetime


# Helpers
def validate_interval(start_date, end_date, raise_exception=True):
    if start_date and not start_date.tzinfo:
        if raise_exception:
            raise Exception("Invalid Start Date: %s Reason: Missing Timezone.")
        else:
            return False

    if end_date and not end_date.tzinfo:
        if raise_exception:
            raise Exception("Invalid End Date: %s Reason: Missing Timezone.")
        else:
            return False

    return True


class TimeUnit:
    # TODO: If using enums:
    # pip install enum34
    # class Unit(Enum):
    second = 0
    minute = 1
    hour = 2
    day = 3
    week = 4
    month = 5
    year = 6
    infinite = 999


# Models
class Provider(object):
    name = None
    identifier = None

    def __init__(self, name, identifier):
        self.name = name
        self.identifier = identifier

    @classmethod
    def from_core(cls, core_provider):
        return cls(name=core_provider.location, identifier=core_provider.id)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<Provider:%s %s>" % (machine.name, machine.identifier)


class Machine(object):
    name = None
    identifier = None

    def __init__(self, name, identifier):
        self.name = name
        self.identifier = identifier

    @classmethod
    def from_core(cls, core_pm):
        return cls(name=core_pm.application.name,
                   identifier=core_pm.identifier)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<Machine:%s %s>" % (machine.name, machine.identifier)


class Size(object):
    name = None
    identifier = None
    cpu = None
    ram = None
    disk = None

    def __init__(self, name, identifier, cpu=0, ram=0, disk=0):
        self.name = name
        self.identifier = identifier
        self.cpu = cpu
        self.ram = ram
        self.disk = disk

    @classmethod
    def from_core(cls, core_size):
        return cls(core_size.name, core_size.alias,
            cpu=core_size.cpu, ram=core_size.mem, disk=core_size.disk)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<Size:%s (ID:%s) %s CPU %s MB RAM %s GB Disk>"\
                % (self.name, self.identifier,
                   self.cpu, self.ram, self.disk)


class Instance(object):
    provider = None
    machine = None
    identifier = None
    history = []

    def __init__(self, identifier, provider=None, machine=None, history=[]):
        self.identifier = identifier
        self.provider = provider
        self.machine = machine
        self.history = history

    @classmethod
    def from_core(cls, core_instance, start_date=None):
        pm = core_instance.provider_machine
        prov = Provider.from_core(pm.provider)
        mach = Machine.from_core(pm)
        size_map = {}
        instance_history = []
        if not start_date:
            # Full list
            history_list = core_instance.instancestatushistory_set.all()
        else:
            # Shorter list
            history_list = core_instance.instancestatushistory_set.filter(
                    Q(end_date=None) | Q(end_date__gt=start_date))
        for history in history_list.order_by('start_date'):
            alloc_history = InstanceHistory.from_core(history)
            instance_history.append(alloc_history)

        # Create the Allocation.Instance object.
        return cls(core_instance.provider_alias,
                prov, mach, instance_history)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<Instance: %s Provider:%s Machine:%s History:%s>"\
                % (self.identifier,
                   self.provider.identifier,
                   self.machine.identifier,
                   self.history)


class InstanceHistory(object):
    start_date = None
    end_date = None
    status = None
    size = None

    def __init__(self, status, size, start_date, end_date):
        validate_interval(start_date, end_date)
        self.status = status
        self.size = size
        self.start_date = start_date
        self.end_date = end_date

    @classmethod
    def from_core(cls, core_history, size=None):
        if not size:
            size = Size.from_core(core_history.size)

        return cls(status=core_history.status.name, size=size,
                   start_date=core_history.start_date,
                   end_date=core_history.end_date)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<InstanceHistory: Status:%s Size:%s Starting:%s Ended:%s>"\
                % (self.status, self.size, self.start_date, self.end_date)


class AllocationIncrease(object):
    """
    AllocationIncrease represents a one-time, positive increase, given on the
    'increase_date'
    """
    amount = 0
    unit = TimeUnit.second
    increase_date = None

    def __init__(self, name, unit, amount, increase_date=None):
        self.name = name
        self.unit = unit
        self.amount = amount
        if unit != TimeUnit.infinite:
            self._validate_input(unit, amount, increase_date)
        self.increase_date = increase_date

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<AllocationIncrease: Increase by: %s On: %s>"\
                % (self.get_credit(), self.increase_date)

    def get_credit(self):
        time_added = self._calculate_time_from_unit_and_amount()
        return time_added

    def _validate_input(self, unit, amount, increase_date):
        if amount <= 0:
            raise ValueError("Bad amount:%s Value must be positive." % amount)
        if not increase_date:
            raise ValueError("Increase_date is required "
            "to know how it fits in a timeperiod")

    def _get_current_date_utc(self):
        return datetime.utcnow().replace(tzinfo = pytz.utc)

    def _days_in_month(self, dt):
        return calendar.monthrange(dt.year, dt.month)[1]

    def _calculate_time_from_unit_and_amount(self):
        """
        To keep things consistent, every unit/amount is converted into days/seconds
        to be added to the timedelta.
        """
        second_amount = 0
        day_amount = 0

        if self.unit == TimeUnit.second:
            second_amount = self.amount
        elif self.unit == TimeUnit.minute:
            second_amount = self.amount * 60
        elif self.unit == TimeUnit.hour:
            second_amount = self.amount * 3600
        elif self.unit == TimeUnit.day:
            day_amount = self.amount
        elif self.unit == TimeUnit.week:
            day_amount = 7 * self.amount
        elif self.unit == TimeUnit.month:
            # NOTE: For now we assume they want N of the 'current month', but we
            #      could make that a variable to avoid any ambiguity..
            day_amount = self._days_in_month(self.increase_date) * self.amount
        elif self.unit == TimeUnit.infinite:
            return timedelta.max
        else:
            raise Exception("Conversion failed: Invalid value '%s'" % self.unit)
        return timedelta(
                days=day_amount,
                seconds=second_amount)


class AllocationUnlimited(AllocationIncrease):

    def __init__(self, increase_date=None):
        if not increase_date:
            increase_date = self._get_current_date_utc()
        super(AllocationUnlimited, self).__init__(
                "Unlimited Allocation",
                TimeUnit.infinite, 1, increase_date)


class AllocationRecharge(AllocationIncrease):
    """
    AllocationRecharge represent the start of a new period of accounting.
    1. Rules engine will evaluate this rule, and add to time_allowed, before
       evaluating any InstanceCountingRule

    (Without a change to the EngineRules:)
    2. For any time PRIOR to the recharge_date, time will NOT be counted.
    3. For any allocation increase PRIOR to the recharge_date, time will NOT be counted.
    """
    recharge_date = None

    def __init__(self, name, unit, amount, recharge_date):
        super(AllocationRecharge, self).__init__(name, unit, amount, recharge_date)
        self.recharge_date = recharge_date

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<AllocationRecharge: Recharge Amount: %s Recharged On: %s>"\
                % (self.get_credit(), self.recharge_date)

class Allocation(object):
    credits = []
    rules = []
    instances = []
    start_date = None
    end_date = None
    interval_delta = None

    def __init__(self, credits, rules, instances,
                 start_date, end_date, interval_delta=None):
        validate_interval(start_date, end_date)
        # TODO: Sort so that Recharges happen PRIOR to Increases on EQUAL dates.
        self.credits = credits
        self.rules = rules
        self.instances = instances
        self.start_date = start_date
        self.end_date = end_date
        self.interval_delta = interval_delta

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "Credits:%s Rules:%s Instances:%s Date Range:%s - %s%s"\
            % (self.credits, self.rules, self.instances,
               self.start_date, self.end_date,
               " Interval Delta:%s" % self.interval_delta \
                      if self.interval_delta else "")
