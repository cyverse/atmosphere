#from django.db import models
#
# NOTE: These are "warlock" models, NOT django models.
from abc import ABCMeta, abstractmethod
import warlock

class TimeUnit:
    #TODO: If using enums:
    # pip install enum34
    # class Unit(Enum):
    second = 0
    minute = 1
    hour = 2
    day = 3
    week = 4
    month = 5
    year = 6


class Rule():
    name = None

class FilterOutRule(Rule):
    """
    These rules determine what InstanceHistory status should 
    be filtered out of calculation
    """
    instance_attr = None
    value = None
    pass
class IgnoreStatusRule(FilterOutRule):
    instance_attr = 'status'
    def _validate_value(self, value):
        if type(value) != str:
            raise Exception("Expects a name to be matched on "
            "InstanceStatusHistory.status")
class IgnoreMachineRule(FilterOutRule):
    instance_attr = 'machine'
    def _validate_value(self, value):
        if type(value) != str:
            raise Exception("Expects a machine UUID to be matched on "
            "Instance.machine.identifier")
class IgnoreProviderRule(FilterOutRule):
    instance_attr = 'provider'
    def _validate_value(self, value):
        if type(value) != str:
            raise Exception("Expects a provider UUID to be matched on "
            "Instance.provider.identifier")


class InstanceCountingRule(Rule):
    """
    Each sub-class represents a way of 'counting time'.
    Instance 
    """
    __metaclass__ = ABCMeta
    pass


class InstanceMultiplierRule(InstanceCountingRule):
    """
    Instance Multiplier Rules.. ALL rules of this type will be applied
    MULTIPLICATIVELY to an instance.
    """
    multiplier = None


class MultiplyBurnTime(InstanceMultiplierRule):
    """
    Ex: BurnTime(.5) + SizeCPU(1)
    Instance 1 : 10 hours used * .5 Burn Time * (1 * )4 CPUs = 20 Hours
    """
    pass


class MultiplySizeCPU(InstanceMultiplierRule):
    """
    Ex: BurnTime(.5) + SizeCPU(1)
    Instance 1 : 10 hours used * .5 Burn Time * (1 * )4 CPUs = 20 Hours
    """
    pass


class MultiplySizeDisk(InstanceMultiplierRule):
    """
    Units here are ALWAYS in GB
    """
    pass


class MultiplySizeRAM(InstanceMultiplierRule):
    """
    Units here are ALWAYS in MB

    Ex: SizeRAM(1GB)
    Instance 1 : 10 hours used * 8GB = 80 Hours
                 ( unit:(1/1024MB) * value:8*1024 MBs)
    """
    def _gb_to_mb(gb_size):
        return gb_size*1024
    def _mb_to_gb(mb_size):
        return mb_size/1024.0


class UnitAndAmountRule(Rule):
    """
    These rules have a name, a unit, & an amount
    Unit = The scope represented by 'amount' (Default:TimeUnit.second)
    Amount to increase is ALWAYS an integer
    """
    amount = 0
    unit = TimeUnit.second


class AllocationRecharge(UnitAndAmountRule):
    """
    AllocationRecharge represent the start of a new period of accounting.
    1. Rules engine will evaluate this rule, and add to time_allowed, before
       evaluating any InstanceCountingRule
    2. For any time PRIOR to the recharge_date, time will NOT be counted.
    3. For any allocation increase PRIOR to the recharge_date, time will NOT be counted.
    """
    recharge_date = None
    pass


class AllocationIncrease(UnitAndAmountRule):
    """
    AllocationIncrease represents a one-time increase in time_allowed
    """
    pass

#################

class Provider():
    name = None
    identifier = None


class Machine():
    name = None
    identifier = None


class Size():
    identifier = None
    cpu = None
    ram = None
    disk = None


class Instance():
    provider = None
    machine = None
    identifier = None
    history = []


class InstanceHistory():
    start_date = None
    end_date = None
    status = None
    size = None


class Allocation():
    start_date = None
    end_date = None
    rules = []
    instances = []

## OUTPUTS
instance_result_schema = {
    "name": "InstanceResult",
    "properties": {
        "used_allocation": { "type": "number" },
        "burn_rate": { "type": "number" },
    }
}
allocation_result_schema = {
    "name": "AllocationResult",
    "properties": {
        "total_allocation": { "type": "number" },
        "used_allocation": { "type": "number" },
        "remaining_allocation": { "type": "number" },
        "burn_rate": { "type": "number" },
        "time_to_zero": { "type": "string" },
        "instance_results": { "type": "array" },
    }
}
InstanceResult = warlock.model_factory(instance_result_schema)
AllocationResult = warlock.model_factory(allocation_result_schema)
