"""
Models for the Results (Output) after running allocation
through the engine.
"""
from django.utils.timezone import timedelta, datetime, now, utc

from allocation import validate_interval
from allocation.models.inputs import \
    AllocationIncrease, AllocationRecharge, AllocationUnlimited, Allocation


class InstanceHistoryResult(object):

    def __init__(self, status_name,
                 clock_time=timedelta(0),
                 total_time=timedelta(0),
                 burn_rate=timedelta(0)):

        self.status_name = status_name

        # Clock time == 'Total'Time used (Without rules applied)
        self.clock_time = clock_time

        # Total time == 'Total'Time used (After rules applied)
        self.total_time = total_time

        # Burn rate == Time used (After rules applied) per second
        self.burn_rate = burn_rate

    def get_total_hours(self):
        return round(
            self.total_time.total_seconds()/3600.0,
            2)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<HistoryResult: Status:%s Clock Time:%s Total Time:%s (%s AU) Burn Rate:%s/0:00:01>" % (
            self.status_name, self.clock_time, self.total_time, self.get_total_hours(), self.burn_rate)


class InstanceResult(object):

    def __init__(self, identifier, history_list):
        self.identifier = identifier
        self.history_list = history_list
    # Group into status results if necessary

    def get_burn_rate(self):
        burn_rates = (status.burn_rate for status in self.history_list)
        return sum(burn_rates, timedelta(0))

    def total_runtime(self):
        total_times = (status.total_time for status in self.history_list)
        return sum(total_times, timedelta(0))

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<InstanceResult: %s Total Runtime:%s>"\
            % (self.identifier, self.total_runtime())


class TimePeriodResult(object):

    def __init__(self, start_date=None, end_date=None,
                 allocation_credit=timedelta(0), instance_results=None):
        validate_interval(start_date, end_date)
        self._allocation_credit = allocation_credit
        # Required
        self.total_credit = allocation_credit

        if not instance_results:
            self.instance_results = []
        else:
            self.instance_results = instance_results

        # Datekeeping
        self.start_counting_date = start_date
        self.stop_counting_date = end_date

    def time_to_zero(self):
        """
        Knowing the 'burn_rate', the total credit, and the stop_counting_date,
        give the 'time until zero' if current conditions continue..
        ASSUMPTION #1: We do not take into account the 'next' monthly recharge,
        etc.

        * This avoids having an "Inifinite" or "N/A" ttz due to recharge
        """
        # As of 'end_date'
        is_over, diff_amount = self.allocation_difference()

        if is_over:
            # TTZ == end_date (Its already over)
            return self.stop_counting_date

        # Looking Into the future
        current_rate = self.get_burn_rate()
        if current_rate == timedelta(0):
            return datetime.max.replace(tzinfo=utc)
        # To move from rate to date
        # divide (seconds remaining) over (seconds per second)
        # To get remaining seconds in the future
        difference = diff_amount.total_seconds()
        rate = current_rate.total_seconds()
        ttz_in_secs = difference / rate

        ttz_delta = timedelta(seconds=ttz_in_secs)
        # NOTE: If we use datetime.max for our allocation credit
        #      then our adding of values causes an OverflowError.
        #      In this case, return timedelta.max to represent 'infinite'
        try:
            ttz_datetime = self.stop_counting_date + ttz_delta
        except OverflowError:
            return datetime.max.replace(tzinfo=utc)
        # Add delta to stop-time to get future ttz.
        return ttz_datetime

    def get_burn_rate(self):
        burnrate = timedelta(0)
        for instance_result in self.instance_results:
            burnrate += instance_result.get_burn_rate()
        return burnrate

    def over_allocation(self):
        """
        Knowing the total allocation, collect total runtime.
        If the difference is LESS THAN//EQUAL to 0, user is OVER Allocation.
        """
        return self.allocation_difference()[0]

    def allocation_difference(self):
        """
        Difference between allocation_credit (Given) and total_runtime (Used)
        Return: (True - Over Allocation, False - Under Allocation
                 Amount over/under allocation)
        """
        total_runtime = self.total_instance_runtime()
        difference = self.total_credit - total_runtime
        is_over = difference <= timedelta(0)
        if is_over:
            #Absolute values required..
            difference = -difference
        return (is_over, difference)

    def increase_credit(self, credit_amount, carry_forward=False):
        """
        Increase the current allocation credit by the credit amount.
        Return the new allocation credit total
        """
        if not carry_forward:
            self._allocation_credit += credit_amount
        self.total_credit += credit_amount
        return self.total_credit

    def total_instance_runtime(self):
        """
        Count the total_time from each status result, for each instance result.
        """
        total_runtime = timedelta(0)
        for instance_result in self.instance_results:
            for status_result in instance_result.history_list:
                total_runtime += status_result.total_time
        return total_runtime

    def __repr__(self):
        return self.__unicode__()

    def _carry_str(self):
        if self.total_credit != self._allocation_credit:
            return " (From Rule: %s, From Carry Over: %s)"\
                % (self._allocation_credit,
                   self.total_credit - self._allocation_credit)
        return ""

    def __unicode__(self):
        return "<TimePeriodResult: Starting From: %s To: %s"\
               "Allocation Credit:%s%s Instance Results:%s>"\
            % (self.start_counting_date, self.stop_counting_date,
               self.total_credit, self._carry_str(), self.instance_results)


class AllocationResult():

    """
    "The Result". This class contains 'all the things'
    """
    allocation = None
    window_start = None
    window_end = None
    time_periods = []
    # POLICY decisions that affect the engine
    carry_forward = False

    @classmethod
    def no_allocation(cls):
        zero_allocation = Allocation([], [], [], None, None)
        return AllocationResult(zero_allocation, None, None)

    def __init__(self, allocation, window_start, window_end, time_periods=[],
                 force_interval_every=None, carry_forward=False):
        if not allocation:
            raise Exception("Allocation is a required parameter")

        self.allocation = allocation
        self.window_start = window_start
        if not window_end:
            window_end = now()
        self.window_end = window_end
        self.carry_forward = carry_forward
        if time_periods:
            self.time_periods = time_periods
        elif force_interval_every:
            self.time_periods = self._time_periods_by_interval(
                force_interval_every)
        else:
            self.time_periods = self._time_periods_by_allocation()

    def total_runtime(self):
        runtime = timedelta(0)
        for period in self.time_periods:
            runtime += period.total_instance_runtime()
        return runtime

    def first_period(self):
        if len(self.time_periods) == 0:
            raise Exception("Cannot retrieve first period"
                            " -- No time periods exist")
        return self.time_periods[-1]

    def last_period(self):
        if len(self.time_periods) == 0:
            raise Exception("Cannot retrieve last period"
                            " -- No time periods exist")
        return self.time_periods[-1]

    def total_credit(self):
        runtime = timedelta(0)
        for period in self.time_periods:
            runtime += period._allocation_credit
        return runtime

    def get_burn_rate(self):
        return self.last_period().get_burn_rate()

    def time_to_zero(self):
        return self.last_period().time_to_zero()

    def total_difference(self):
        """
        Returns 2-tuple:
        (over_allocation-True/under_allocation-False, amount_over_or_under)
        """
        if self.carry_forward:
            return self.last_period().allocation_difference()
        over_allocation = False
        total_diff_credit = timedelta(0)
        total_diff_overage = timedelta(0)
        for period in self.time_periods:
            is_over, difference = period.allocation_difference()
            if is_over:
                total_diff_overage += difference
            else:
                total_diff_credit += difference
            #Keep your math in order -- dealing with absvalues (and -timedelta means something else)!
            if total_diff_overage > total_diff_credit:
                over_allocation = True
                total_diff = total_diff_overage - total_diff_credit
            else:
                over_allocation = False
                total_diff = total_diff_credit - total_diff_overage
        return (over_allocation, total_diff)

    def over_allocation(self):
        return any(period.over_allocation() for period in self.time_periods)

    def _credit_by_interval(self, time_periods):
        """
        When we create a list by interval, we still need to go through and
        check where AllocationRecharge//AllocationIncrease credits will go.
        """
        # NOTE: This is sorted! We can guarantee order!
        for current_period in time_periods:
            for allocation_credit in sorted(self.allocation.credits,
                                            key=lambda c: c.increase_date):
                inc_date = allocation_credit.increase_date
                # Ignore credits that happened PRIOR to or AT/AFTER
                # your counting dates.
                if inc_date < current_period.start_counting_date or\
                   inc_date >= current_period.stop_counting_date:
                    continue
                # Increase the credit and move along
                current_period.increase_credit(allocation_credit.get_credit())
        return time_periods

    @classmethod
    def _sort_credit_type(cls, credit):
        """
        A comparision method which compares whether the credit is a recharge
        or not
        """
        if credit.__class__ == AllocationRecharge:
            return 0
        else:
            return 1

    def _time_periods_by_interval(self, tdelta):
        """
        Given a timedelta, evenly divide up your TimePeriod
        """
        time_periods = []
        time_period = TimePeriodResult(self.window_start, None)
        current_date = self.window_start + tdelta
        while current_date < self.window_end:
            # Finish this interval
            time_period.stop_counting_date = current_date
            time_periods.append(time_period)
            # Start next interval
            time_period = TimePeriodResult(current_date, None)
            current_date += tdelta
        time_period.stop_counting_date = self.window_end
        time_periods.append(time_period)
        self._credit_by_interval(time_periods)
        return time_periods

    def _time_periods_by_allocation(self):
        """
        Given a list of credits to the allocation, logically divide up
        """
        time_periods = []
        current_period = TimePeriodResult(self.window_start, None)

        key_fn = lambda credit: (credit.increase_date,
                                 AllocationResult._sort_credit_type(credit))

        # NOTE: This is sorted! We can guarantee order!
        for allocation_credit in sorted(self.allocation.credits, key=key_fn):
            # Sanity Checks..
            if allocation_credit.increase_date < self.window_start:
                raise ValueError(
                    "Bad Allocation Credit:%s requests an increase"
                    "PRIOR to the start of accounting [%s]"
                    % (allocation_credit, self.window_start))
            elif allocation_credit.increase_date > self.window_end:
                raise ValueError(
                    "Bad Allocation Credit:%s requests an increase"
                    "AFTER the end of accounting [%s]"
                    % (allocation_credit, self.window_end))

            # When NOT to create a new time period:
            if allocation_credit.__class__ in [AllocationIncrease,
                                               AllocationUnlimited]:
                # AllocationIncrease at any stage, add it to the current period
                current_period.increase_credit(allocation_credit.get_credit())
                continue
            elif allocation_credit.__class__ != AllocationRecharge:
                raise ValueError("Invalid Object:%s passed in credits"
                                 % allocation_credit)
            # NOTE: ASSERT: Past this line we deal with AllocationRecharge

            if allocation_credit.recharge_date == self.window_start:
                # the increase date conveniently matches the time that we are
                # accounting. Increase time only and move along.
                current_period.increase_credit(allocation_credit.get_credit())
                continue
            # End & start the 'current_period'
            current_period.stop_counting_date = allocation_credit.recharge_date
            time_periods.append(current_period)
            current_period = TimePeriodResult(
                allocation_credit.recharge_date, None,
                allocation_credit.get_credit())
        # End the 'final' current_period and return
        current_period.stop_counting_date = self.window_end
        time_periods.append(current_period)
        return time_periods

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<AllocationResult: Time Periods: %s "\
            % (self.time_periods)
