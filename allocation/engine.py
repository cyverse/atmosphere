"""
The Allocation Engine --

Takes as input a Warlock-Defined 'Allocation' Object.
Returns as output the amount of allocation consumed.

TODO: Refactor #1 - have one AllocationResult PER INSTANCE so that each can be individually evaluated, printed

    #TODO: Do we have rules that 'use time' that are NOT
    # directed at instances? (Global?)
"""
from allocation.models import AllocationResult, InstanceResult
from datetime import timedelta, datetime
import calendar, pytz

### Utils ###

def _to_datestring(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def _to_datetime(date_string):
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

def _days_in_month(dt):
    return calendar.monthrange(dt.year, dt.month)[1]

def _get_current_date_utc():
    return datetime.utcnow().replace(tzinfo = pytz.utc)

### Main ###
def calculate_allocation(allocation):
    instance_results = _get_instance_results(allocation)

    seconds_used = burn_rate = 0
    for result in instance_results:
        seconds_used += result.used_allocation
        burn_rate += result.burn_rate

    time_allowed = _get_time_allowed(allocation)
    seconds_allowed = time_allowed.total_seconds()

    seconds_remaining = seconds_allowed-seconds_used
    end_date = _to_datetime(allocation.end_date)
    time_to_zero = _get_ttz(end_date, seconds_remaining, burn_rate)

    return AllocationResult(
            total_allocation = seconds_allowed,
            used_allocation = seconds_used,
            remaining_allocation = seconds_remaining,
            burn_rate=burn_rate,
            time_to_zero=_to_datestring(time_to_zero),
            instance_results=instance_results)

def _get_instance_results(allocation):
    start_date = _to_datetime(allocation.start_date)
    end_date = _to_datetime(allocation.end_date)
    instance_results = []
    for instance in allocation.instances:
        instance_results.append(
                _calculate_instance_result_cumulatively(
                    instance, allocation.rules, start_date, end_date))
    return instance_results

def _calculate_instance_result_cumulatively(instance, rules, start_date, end_date):
    """
    time_used = 500 seconds
    time_used * 2 CPU * 4GB RAM * 0 Burn Rate = 0 Seconds
    """
    burn_rate = time_used = timedelta(0)
    one_second_prior = end_date - timedelta(seconds=1)

    print "History of instance:%s" % instance.identifier
    # Calculate time used by applying rules to each history and keeping a
    # running total
    for history in instance.history:
        if history.status != 'active':
            continue
        time_used += _apply_rules(
                history, rules,
                start_date, end_date)

    # Calculate burn rate by applying rules to last history
    # (given a one second delta) to determine how much time is burned/second
    last_history = instance.history[-1]
    burn_rate = _apply_rules(
            last_history, rules,
            one_second_prior, end_date)
    return InstanceResult(
            used_allocation=time_used.total_seconds(),
            burn_rate=burn_rate.total_seconds())

def _apply_rules(history, rules, start_date, end_date):
    time_used = _calculate_time_used(history, start_date, end_date)
    for rule in rules:
        if rule.type == 'increase_allocation':
            continue
        multiplier = _get_multiplier(rule, history)
        time_used *= multiplier * rule.amount
    return time_used

def _get_multiplier(rule, history):
    if rule.type == 'size_ram':
        multiplier = history.size.ram
    elif rule.type == 'size_cpu':
        multiplier = history.size.cpu
    elif rule.type == 'size_disk':
        multiplier = history.size.disk
    elif rule.type == 'burn_rate':
        multiplier = 1
    else:
        raise Exception("Cannot calcualte Rule. Unknown Type: %s " % rule.type)
    return multiplier



## Time Allowed ##
def _get_time_allowed(allocation):
    time_allowed = timedelta(0)
    for rule in allocation.rules:
        if rule.type == "increase_allocation":
            time_increase = _increase_allocation(rule)
            time_allowed += time_increase
    return time_allowed

def _increase_allocation(rule):
    return _increase_by_amount(rule.amount, rule.unit)

def _increase_by_amount(amount, unit):
    second_amount = 0
    day_amount = 0
    if unit == 'month':
        curr_date = _get_current_date_utc()
        day_amount = _days_in_month(curr_date) * amount
    elif unit == 'week':
        day_amount = 7 * amount
    elif unit == 'day':
        day_amount = amount
    elif unit == 'hour':
        second_amount = amount * 3600
    elif unit == 'minute':
        second_amount = amount * 60
    elif unit == 'second':
        second_amount = amount
    else:
        raise Exception("Conversion failed: Invalid value '%s'" % unit)
    return timedelta(days=day_amount, seconds=second_amount)

## Time Used ##
def _calculate_time_used(instance_history, start_date, end_date):
    instance_start_date = _to_datetime(instance_history.start_date)
    instance_end_date = _to_datetime(instance_history.end_date)

    # Expiry Check -- If this instance history 
    # ended prior to the beginning of
    # the 'check range' it should not be counted.
    if instance_end_date < start_date:
        return timedelta(0)

    if instance_start_date >= start_date:
        #Use instance start date IF later than beginning of range
        use_start = instance_start_date
    else:
        use_start = start_date

    if instance_end_date <= end_date:
        #Use instance end date IF earlier than end of range
        use_end = instance_end_date
    else:
        use_end = end_date

    time_used = use_end - use_start
    return time_used


## Burn Rate
def _get_ttz(end_date, seconds_remaining, burned_per_second):
    if burned_per_second >= 1:
        #If the BurnRate is non-zero, we divide the amount burned per second by
        # the amount of seconds the user has left. The result is the # of
        # seconds from the end date until the user is OUT of allocation, with
        # all things remaining constant.
        remaining_time = seconds_remaining / burned_per_second
    elif seconds_remaining <= 0:
        #If the burn rate is zero and we are OUT of time we can still calculate
        # how long ago one ran out of allocation (When they should have been
        # stopped from using the machine).
        remaining_time = seconds_remaining
    else:
        #The burn rate is zero but there is remaining time to be used.
        # In these cases it is impossible to calculate a valid result
        # TODO: Return the epoch or some "NIL" date string instead?
        return None
    return end_date + timedelta(seconds=remaining_time)

#######
#OLD DO NOT USE .. FOR REFERENCE ONLY!
#######

def _calculate_instance_result_individually(instance, rules, start_date, end_date):
    """
    TODO: We may want to combine multipliers when we have more than 2 results..
    Example of when this matters:

    time_used = 500 seconds
    time_used * 0 BurnRate =    0 Seconds
    time_used * 2 CPU      = 1000 Seconds
    time_used * 4GB RAM    = 2000 Seconds
                             ============
                             3000 Seconds
    """
    burn_rate = time_used = timedelta(0)
    one_second_prior = end_date - timedelta(seconds=1)

    print "History of instance:%s" % instance.identifier
    for history in instance.history:
        for rule in rules:
            if rule.type == 'increase_allocation':
                continue
            time_used += _calculate_rule(rule, history, start_date, end_date)
            #Using ONLY the last history object, looking at one second before
            # end date of the history, run over all rules to determine if 
            # the instance is still 'burning' time.
            if history == instance.history[-1]:
                burn_rate += _calculate_rule(rule, history, one_second_prior, end_date)
    return InstanceResult(
            used_allocation=time_used.total_seconds(),
            burn_rate=burn_rate.total_seconds())

def _calculate_rule(rule, history, start_date, end_date):
    if history.status != 'active':
        return timedelta(0)

    time_used = _calculate_time_used(history, start_date, end_date)
    multiplier = _get_multiplier(rule, history)
    result = time_used * multiplier * rule.amount
    print "%s * %s(%s) * %s = %s  | FROM:%s TO:%s"\
            % (time_used, multiplier,
               rule.type, rule.amount, result, start_date, end_date)
    return result
