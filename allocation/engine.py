"""
The Allocation Engine --

Takes as input a Warlock-Defined 'Allocation' Object.
Returns as output the amount of allocation consumed.

TODO: Refactor #1 - have one AllocationResult PER INSTANCE so that each can be
      individually evaluated, printed

    #TODO: Do we have rules that 'use time' that are NOT
    # directed at instances? (Global?)
"""
import pytz

from django.utils.timezone import timedelta, datetime

from threepio import logger

from allocation.models import AllocationResult, GlobalRule, InstanceResult,\
    InstanceRule, InstanceHistoryResult


def _get_zero_date_utc():
    # "Epoch Date" 1-1-1970 0:00:00 UTC
    return datetime(1970, 1, 1).replace(tzinfo=pytz.utc)


def _get_current_date_utc():
    return datetime.utcnow().replace(tzinfo=pytz.utc)


def get_allocation_window(allocation,
                          default_start_date=_get_zero_date_utc(),
                          default_end_date=_get_current_date_utc()):
    """
    Returns a tuple containing the allocation windows start and end date
    """
    if not allocation.start_date:
        window_start_date = default_start_date
    else:
        window_start_date = allocation.start_date

    if not allocation.end_date:
        window_end_date = default_end_date
    else:
        window_end_date = allocation.end_date

    return window_start_date, window_end_date


# Main ###
def calculate_allocation(allocation, print_logs=False):
    (window_start_date, window_end_date) = get_allocation_window(allocation)

    # FYI: Calculates time periods based on allocation.credits
    current_result = AllocationResult(
        allocation, window_start_date, window_end_date,
        force_interval_every=allocation.interval_delta)

    if print_logs:
        logger.debug(
            "New AllocationResult, Start On & (End On): %s (%s)"
            % (current_result.window_start, current_result.window_end))
    instance_rules = []
    # First loop - Apply all global rules.
    #             Collect instance rules seperately.
    for rule in allocation.rules:
        if issubclass(rule.__class__, GlobalRule):
            rule.apply_global_rule(allocation, current_result)
        elif issubclass(rule.__class__, InstanceRule):
            # Non-global rules assumed to be applied at instance-level.
            # Keeping them seperate for now..
            instance_rules.append(rule)
        else:
            raise Exception("Unknown Type of Rule: %s" % rule)
    time_forward = timedelta(0)
    for current_period in current_result.time_periods:
        if current_result.carry_forward and time_forward:
            current_period.increase_credit(time_forward, carry_forward=True)

        if print_logs:
            logger.debug("> New TimePeriodResult: %s" % current_period)
            if current_period.total_credit > timedelta(0):
                logger.debug("> > Allocation Increased: %s"
                             % current_period.total_credit)
        # Second loop - Go through all the instances and apply
        #              the specific rules (This loop relates to time USED)
        instance_results = []

        for instance in allocation.instances:
            # "Chatty" Warning - Uncomment at your own risk
            # logger.debug("> > Calculating Instance history:%s"
            #             % instance.identifier)
            if not instance:
                continue
            history_list = _calculate_instance_history_list(
                instance, instance_rules,
                current_period.start_counting_date,
                current_period.stop_counting_date,
                print_logs=print_logs)
            if not history_list:
                continue
            instance_result = InstanceResult(
                identifier=instance.identifier, history_list=history_list)
            instance_results.append(instance_result)

        if print_logs:
            logger.debug("> > Instance history Results:")
            for instance_result in instance_results:
                logger.debug("> > %s" % instance_result)
        current_period.instance_results = instance_results
        is_over, diff_amount = current_period.allocation_difference()
        if print_logs:
            logger.debug("> > %s - %s = %s %s" %
                         (current_period.total_credit,
                          current_period.total_instance_runtime(),
                          "-" if is_over else "",
                          diff_amount))
        if current_result.carry_forward:
            # We need to 'carry forward the negative value'
            # to appropriately 'credit' the next month.
            time_forward = -diff_amount if is_over else diff_amount
    return current_result


def _multiply_time_delta(timedelta1, timedelta2):
    time_seconds = timedelta1.total_seconds() *\
        timedelta2.total_seconds()
    return timedelta(seconds=time_seconds)


def _calculate_instance_history_list(instance, rules, start_date, end_date,
                                     print_logs=False):
    """
    Given an instance and a set of 'InstanceRules'
    Calculate the time used for every history
    """
    # Calculate time used by applying rules to each history and keeping a
    # running total for each status
    history_list = []
    for history in instance.history:
        history_result = InstanceHistoryResult(status_name=history.status)
        if history.end_date and history.end_date < start_date:
            history_result.clock_time = timedelta(0)
            history_list.append(history_result)
            continue

        clock_time = _get_clock_time(history, start_date, end_date,
                                     print_logs=print_logs)

        if clock_time == timedelta(0):
            # do we need this? seems like it could cause unforseen problems
            history_result.clock_time = clock_time
            history_list.append(history_result)
            continue

        # NOTE: There are some limitations to an implementation like this
        #       Ex: A rule that starts 'halfway' between start and end date
        #          (Is that a thing?)
        time_per_second = _running_time_per_second(history, instance, rules)
        running_time = _multiply_time_delta(clock_time, time_per_second)
        history_result.clock_time += clock_time
        history_result.total_time += running_time

        if _get_burn_rate_test(history, end_date):
            history_result.burn_rate += time_per_second
        history_list.append(history_result)

    return history_list


def _get_burn_rate_test(history, end_date):
    """
    If the Instance History carries forward PAST the stop_counting_date
    Calculate the amount of time burned per second.
    """
    if history.start_date > end_date:
        return False
    if not history.end_date or history.end_date >= end_date:
        return True
    return False


def _get_clock_time(instance_history, start_date, end_date, print_logs=True):
    """
    Based on the current instance history, how much time 'on the clock'
    was used between 'start_date' and 'end_date'?
    """
    instance_start_date = instance_history.start_date
    instance_end_date = instance_history.end_date
    # Expiry (Sanity) Check -- If this instance history
    # ended PRIOR TO the beginning of date range
    # return 0 Time used.
    if instance_end_date and instance_end_date < start_date:
        return timedelta(0)
    # Prior (Sanity) Check -- If this instance history
    # began AFTER the end of the date range
    # return 0 Time used. (No negative time in the real world!)
    if instance_start_date and instance_start_date > end_date:
        return timedelta(0)

    # When to start the clock:
    if instance_start_date >= start_date:
        # Start at beginning of the history if later than start_date.
        use_start = instance_start_date
    else:
        # IGNORE The history that existed prior to the time we started counting
        use_start = start_date

    # When to stop the clock:
    if instance_end_date and instance_end_date <= end_date:
        # Stop at the end of the history if earlier than end_date.
        use_end = instance_end_date
    else:
        # IGNORE The history that existed AFTER the time we stopped counting
        use_end = end_date

    clock_time = use_end - use_start
    if print_logs:
        logger.debug(">> Clock time: %s - %s = %s"
                     % (use_end, use_start, clock_time))
    return clock_time


def _running_time_per_second(history, instance, rules):
    running_time = timedelta(seconds=1)
    for rule in rules:
        # Each rule is given the previous running_time, and
        # returns it as a result
        running_time = rule.apply_rule(instance, history, running_time)
    return running_time
