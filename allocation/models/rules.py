"""
The list of Rules (Input for allocation)
GlobalRules:
* Rules will be applied that change how the engine is run, or
  specific attributes to the AllocationResult object. (Like an increase)
InstanceRules:
* Each rule will be applied individually on a specific instance history
* In adition to the history and the current running_time

TODO: We have 'Ignore*Rule', it might be nice to have a 'Match*Rule' class
      to define what you DO want counted.. rather than what you don't...
"""
from abc import ABCMeta

from threepio import logger


# Utils
def _needle_in_haystack(haystack, needle):
    for value in haystack:
        if value == needle:
            return True
    return False


# Level 1
class Rule():
    __metaclass__ = ABCMeta

    def __init__(self, name):
        self.name = name


# Level 2
class GlobalRule(Rule):

    """
    """

    def apply_global_rule(self, allocation, allocation_result):
        raise NotImplementedError("Should be implemented by subclass.")


class InstanceRule(Rule):

    """
    """

    def apply_rule(self, instance, history, running_time, print_logs=False):
        raise NotImplementedError("Should be implemented by subclass.")


class EngineRule(GlobalRule):

    """
    """


# Level 3
class CarryForwardTime(EngineRule):

    """
    When there is "leftover" time between TimePeriods, carry forward the time.
    """

    def apply_global_rule(self, allocation, allocation_result):
        allocation_result.carry_forward = True

    def __init__(self, name=None):
        if not name:
            name = "Carry Forward between TimePeriodResults"
        super(CarryForwardTime, self).__init__(name)


class FilterOutRule(InstanceRule):

    """
    These rules determine what InstanceHistory status should
    be filtered out of calculation
    """
    __metaclass__ = ABCMeta
    instance_attr = None
    value = None

    def __init__(self, name, value):
        super(FilterOutRule, self).__init__(name)
        self.value = value


class InstanceCountingRule(InstanceRule):

    """
    Each sub-class represents a way of 'counting time'.
    Instance
    """
    __metaclass__ = ABCMeta

    def __init__(self, name):
        super(InstanceCountingRule, self).__init__(name)


class InstanceMultiplierRule(InstanceCountingRule):

    """
    Instance Multiplier Rules.. ALL rules of this type will be applied
    MULTIPLICATIVELY to an instance.
    """
    __metaclass__ = ABCMeta
    multiplier = None

    def __init__(self, name, multiplier):
        super(InstanceMultiplierRule, self).__init__(name)
        self.multiplier = multiplier


# Types of 'FilterOutRule'
class IgnoreStatusRule(FilterOutRule):

    def __init__(self, name, value):
        super(IgnoreStatusRule, self).__init__(name, value)
        self.instance_attr = 'status'

    def apply_rule(self, instance, history, running_time, print_logs=False):
        """
        If a match is found between Status History and the 'needle'
        Then the running_time should be ZEROed.
        """
        if not isinstance(self.value, list):
            values = [self.value]
        else:
            values = self.value
        found_match = _needle_in_haystack(values, history.status)
        if found_match:
            running_time *= 0
            if print_logs:
                logger.debug(">> Ignore Instance Status '%s'. Set Runtime to 0"
                             % (history.status))
        # All misses.
        return running_time

    def _validate_value(self, value):
        if not isinstance(value, str):
            raise Exception("Expects a name to be matched on "
                            "InstanceStatusHistory.status")


class IgnoreMachineRule(FilterOutRule):

    def __init__(self, name, value):
        super(IgnoreMachineRule, self).__init__(name, value)
        self.instance_attr = 'machine'

    def _validate_value(self, value):
        if not isinstance(value, str):
            raise Exception("Expects a machine UUID to be matched on "
                            "Instance.machine.identifier")

    def apply_rule(self, instance, history, running_time, print_logs=False):
        """
        If a match is found between Machine UUID and the 'needle'
        Then the running_time should be ZEROed.
        """
        if not isinstance(self.value, list):
            values = [self.value]
        else:
            values = self.value
        found_match = _needle_in_haystack(values, instance.machine.identifier)
        if found_match:
            running_time *= 0
            if print_logs:
                logger.debug(">> Ignore Machine identifier '%s'."
                             "Set Runtime to 0" % (history.status))
        return running_time


class IgnoreProviderRule(FilterOutRule):

    def _validate_value(self, value):
        if not isinstance(value, str):
            raise Exception("Expects a provider UUID to be matched on "
                            "Instance.provider.identifier")

    def apply_rule(self, instance, history, running_time, print_logs=False):
        """
        If a match is found between Provider ID and the 'needle'
        Then the running_time should be ZEROed.
        """
        if not isinstance(self.value, list):
            values = [self.value]
        else:
            values = self.value
        found_match = _needle_in_haystack(values, instance.provider.identifier)
        if found_match:
            running_time *= 0
            if print_logs:
                logger.debug(">> Ignore Provider identifier '%s'."
                             "Set Runtime to 0"
                             % (history.status))
        return running_time

    def __init__(self, name, value):
        super(IgnoreProviderRule, self).__init__(name, value)
        self.instance_attr = 'provider'


# Types of 'InstanceCountingRule'
class MultiplyBurnTime(InstanceMultiplierRule):

    def apply_rule(self, instance, history, running_time, print_logs=False):
        """
        Multiply the running_time by (multiplier) to adjust the overall burn
        time.
        """
        if print_logs:
            logger.debug(">> %s Current Running Time:%s * Multiplier:%s = %s"
                         % (history.status, running_time, self.multiplier,
                            running_time * self.multiplier))
        running_time *= self.multiplier
        return running_time

    def __init__(self, name, multiplier):
        super(MultiplyBurnTime, self).__init__(name, multiplier)


class MultiplySizeCPU(InstanceMultiplierRule):

    def apply_rule(self, instance, history, running_time, print_logs=False):
        """
        Multiply the running_time by size of CPU * (multiplier)
        """
        if print_logs:
            logger.debug(
                ">> %s Current Running Time:%s * CPU:%s * Multiplier:%s = %s"
                % (history.status, running_time, history.size.cpu,
                   self.multiplier,
                   running_time * history.size.cpu * self.multiplier))
        running_time *= self.multiplier * history.size.cpu
        return running_time

    def __init__(self, name, multiplier):
        super(MultiplySizeCPU, self).__init__(name, multiplier)


class MultiplySizeDisk(InstanceMultiplierRule):

    """
    Units here are ALWAYS in GB
    """

    def apply_rule(self, instance, history, running_time, print_logs=False):
        """
        Multiply the running_time by size of Disk (GB) * (multiplier)
        """
        if print_logs:
            logger.debug(
                ">> %s Current Running Time:%s * Disk:%s * Multiplier:%s = %s"
                % (history.status, running_time, history.size.disk,
                   self.multiplier,
                   running_time * history.size.disk * self.multiplier))
        running_time *= self.multiplier * history.size.disk
        return running_time

    def __init__(self, name, multiplier):
        super(MultiplySizeDisk, self).__init__(name, multiplier)


class MultiplySizeRAM(InstanceMultiplierRule):

    """
    Units here are ALWAYS in MB

    Ex: SizeRAM(1GB)
    Instance 1 : 10 hours used * 8GB = 80 Hours
                 ( unit:(1/1024MB) * value:8*1024 MBs)
    """

    def _gb_to_mb(gb_size):
        return gb_size * 1024

    def _mb_to_gb(mb_size):
        return mb_size / 1024.0

    def apply_rule(self, instance, history, running_time, print_logs=False):
        """
        Multiply the running_time by size of RAM (MB) * (multiplier)
        NOTE: To calculate in GB, set self.multiplier = 1/1024
        """
        if print_logs:
            logger.debug(
                ">> %s Current Running Time:%s * RAM:%s * Multiplier:%s = %s"
                % (history.status, running_time, history.size.disk,
                   self.multiplier,
                   running_time * history.size.disk * self.multiplier))
        running_time *= self.multiplier * history.size.ram
        return running_time

    def __init__(self, name, multiplier):
        super(MultiplySizeRAM, self).__init__(name, multiplier)
