"""
The Allocation Engine --

Takes as input a Warlock-Defined 'Allocation' Object.
Returns as output the amount of allocation consumed.

TODO: Refactor #1 - have one AllocationResult PER INSTANCE so that each can be individually evaluated, printed

    #TODO: Do we have rules that 'use time' that are NOT
    # directed at instances? (Global?)


    #TODO: Include time to zero
"""
from allocation.models import AllocationResult, InstanceResult, InstanceStatusResult
from allocation.models import TimeUnit, AllocationRecharge,\
        GlobalRule,InstanceRule
from django.utils.timezone import timedelta, datetime
import calendar, pytz

### Utils (IF we decide to use Warlock, we will need this... ###

def _get_zero_date_utc():
    #"Epoch Date" 1-1-1970 0:00:00 UTC
    return datetime(1,1,1970).replace(tzinfo = pytz.utc)

def _get_current_date_utc():
    return datetime.utcnow().replace(tzinfo = pytz.utc)

### Main ###
def calculate_allocation(allocation):
    if not allocation.start_date:
        window_start_date = _get_zero_date_utc()
    else:
        window_start_date = allocation.start_date

    if not allocation.end_date:
        window_end_date = _get_current_date_utc()
    else:
        window_end_date = allocation.end_date

    #FYI: Calculates time periods based on allocation.credits
    current_result = AllocationResult(allocation,
            window_start_date, window_end_date,
            force_interval_every=allocation.interval_delta)


    print "New AllocationResult, Start On & (End On): %s (%s)"\
            % (current_result.window_start,
               current_result.window_end)
    instance_rules = []
    #First loop - Apply all global rules.
    #             Collect instance rules seperately.
    for rule in allocation.rules:
        if issubclass(rule.__class__, GlobalRule):
            rule.apply_global_rule(allocation, current_result)
        elif issubclass(rule.__class__, InstanceRule):
            #Non-global rules assumed to be applied at instance-level.
            #Keeping them seperate for now..
            instance_rules.append(rule)
        else:
            raise Exception("Unknown Type of Rule: %s" % rule)
    time_forward = timedelta(0)
    for current_period in current_result.time_periods:
        if current_result.carry_forward and time_forward:
            current_period.increase_credit(time_forward, carry_forward=True)

        print "> New TimePeriodResult: %s" % current_period
        if current_period.total_credit > timedelta(0):
            print "> > Allocation Increased: %s" %\
                    current_period.total_credit
        #Second loop - Go through all the instances and apply
        #              the specific rules (This loop relates to time USED)
        instance_results = []

        for instance in allocation.instances:
            #print "> > Calculating Instance Status:%s" % instance.identifier
            status_list = _calculate_instance_status_list(
                instance, instance_rules,
                current_period.start_counting_date,
                current_period.stop_counting_date)
            instance_result = InstanceResult(
                    identifier=instance.identifier,
                    status_list=status_list)
            instance_results.append(instance_result)

        print "> > Instance Status Results:"
        for instance_result in instance_results:
            print "> > %s" % instance_result
        current_period.instance_results = instance_results

        print "> > %s - %s = %s" %\
                (current_period.total_credit,
                current_period.total_instance_runtime(),
                current_period.allocation_difference())
        if current_result.carry_forward:
            time_forward = current_period.allocation_difference()
    return current_result

def _calculate_instance_status_list(instance, rules, start_date, end_date):
    """
    Given an instance and a set of 'InstanceRules'
    Calculate the time used for every unique status name-change.
    """
    # Calculate time used by applying rules to each history and keeping a
    # running total for each status
    status_map = {}
    for history in instance.history:
        status_result = status_map.get(history.status)
        if not status_result:
            status_result = InstanceStatusResult(status_name=history.status)
        #    print ">> Creating Status Result for: %s" % history.status
        #else:
        #    print ">> Updating %s" % status_result
        total_time = _get_running_time(history, instance, rules, start_date, end_date)
        status_result.total_time += total_time
        # If the Instance History carries forward PAST the stop_counting_date
        # Calculate the amount of time burned per second.
        if _get_burn_rate_test(history, end_date):
            burn_rate = _get_burn_rate(history, instance, rules, end_date)
            status_result.burn_rate += burn_rate
        #DEV NOTE: Clock time may not be necessary to carry forward, but we will leave it in for now..
        clock_time = _get_clock_time(history, start_date, end_date, False)
        status_result.clock_time += clock_time
        #Save the current calculation for this status-type and
        # re-use next time that we see it
        #print ">> New Status Result: %s" % status_result
        status_map[history.status] = status_result

    #Keys aren't important, but the objects behind them are..
    return status_map.values()

def _get_burn_rate_test(history, end_date):
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

    #When to start the clock:
    if instance_start_date >= start_date:
        #Start at beginning of the history if later than start_date.
        use_start = instance_start_date
    else:
        #IGNORE The history that existed prior to the time we started counting
        use_start = start_date

    #When to stop the clock:
    if instance_end_date and instance_end_date <= end_date:
        #Stop at the end of the history if earlier than end_date.
        use_end = instance_end_date
    else:
        #IGNORE The history that existed AFTER the time we stopped counting
        use_end = end_date

    clock_time = use_end - use_start
    if print_logs:
        print ">> Counted time: %s - %s = %s" % (use_end, use_start, clock_time)
    return clock_time

def _get_burn_rate(history, instance, rules, end_date):
    """
    The burn rate is a special kind of running time, it applies to the last 'known' second.
    """
    one_second_prior = end_date - timedelta(seconds=1)
    burn_rate = _get_running_time(
            history, instance, rules,
            one_second_prior, end_date, False)
    return burn_rate

def _get_running_time(history, instance, rules, start_date, end_date, print_logs=False):
    """
    Given a SPECIFIC history, an instance, a list of rules, and specified
    start&end date,
    calculate the time used (AKA Clock time)
    return the "running time" after applying all instance rules.
    """
    #Initially (Without any rules executed)
    # The running_time == clock_time
    running_time = _get_clock_time(history, start_date, end_date, print_logs=print_logs)

    #Short-Circuit Test
    if running_time == timedelta(0):
        #TODO: Remove this If we have a rule that DOESN'T use multipliers..
        return running_time

    for rule in rules:
        #Each rule is given the previous running_time, and returns it as a result
        running_time = rule.apply_rule(instance, history, running_time,
                                       print_logs=print_logs)

    #After applying all the rules, the running time has been calculated.
    return running_time
