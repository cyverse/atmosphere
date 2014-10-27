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


class UnitAndAmountRule(Rule):
    """
    These rules have a name, a unit, & an amount
    Unit = The scope represented by 'amount' (Default:TimeUnit.second)
    Amount to increase is ALWAYS an integer
    """
    amount = 0
    unit = TimeUnit.second


class InstanceCountingRule(Rule):
    """
    Each sub-class represents a way of 'counting time' 
    """
    __metaclass__ = ABCMeta
    pass


class InstanceMultiplierRule(InstanceCountingRule):
    """
    Instance Multiplier Rules.. All rules of this type will be applied
    multiplicatively to an instance.
    Ex: BurnTime(.5) + SizeCPU(1)
    Instance 1 : 10 hours used * .5 Burn Time * (1 * )4 CPUs = 20 Hours
    """
    multiplier = None


class MultiplyBurnTime(InstanceMultiplierRule):
    pass


class MultiplySizeCPU(InstanceMultiplierRule):
    pass


class MultiplySizeDisk(InstanceMultiplierRule):
    pass


class MultiplySizeRAM(InstanceMultiplierRule):
    pass


class IncreaseAllocation(UnitAndAmountRule):
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
