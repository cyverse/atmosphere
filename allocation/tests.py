from dateutil.relativedelta import relativedelta
import pytz

from django.test import TestCase
from django.utils import unittest
from django.utils.timezone import datetime, timedelta

from allocation import engine
from allocation.models import Provider, Machine, Size, Instance, \
    InstanceHistory
from allocation.models import Allocation,\
    MultiplySizeCPU, MultiplySizeRAM,\
    MultiplySizeDisk, MultiplyBurnTime,\
    AllocationIncrease, TimeUnit,\
    IgnoreStatusRule, CarryForwardTime, Rule, validate_interval

from core.models import Instance as CoreInstance

# For testing..
openstack = Provider(
    name="iPlant Cloud - Tucson", identifier="4")
openstack_workshop = Provider(
    name="iPlant Cloud Workshop - Tucson", identifier="5")

random_machine = Machine(
    name="Not real machine",
    identifier="12412515-1241-3fc8-bc13-10b03d616c54")
random_machine_2 = Machine(
    name="Not real machine", identifier="39966e54-9282-4fc8-bc13-10b03d616c54")


tiny_size = Size(
    name='Kids Fry', identifier='test.tiny', cpu=1, ram=1024*2, disk=0)
small_size = Size(
    name='Small Fry', identifier='test.small', cpu=2, ram=1024*4, disk=60)
medium_size = Size(
    name='Medium Fry', identifier='test.medium', cpu=4, ram=1024*16, disk=120)
large_size = Size(
    name='Large Fry', identifier='test.large', cpu=8, ram=1024*32, disk=240)


AVAILABLE_PROVIDERS = {
    "openstack": openstack,
    "workshop": openstack_workshop
}


AVAILABLE_MACHINES = {
    "machine1": random_machine,
    "machine2": random_machine_2,
}


AVAILABLE_SIZES = {
    "test.tiny": tiny_size,
    "test.small": small_size,
    "test.medium": medium_size,
    "test.large": large_size
}

STATUS_CHOICES = frozenset(["active", "suspended"])

# Rules
carry_forward = CarryForwardTime()

multiply_by_ram = MultiplySizeRAM(
    name="Multiply TimeUsed by Ram (*1GB)", multiplier=(1/1024))
multiply_by_cpu = MultiplySizeCPU(
    name="Multiply TimeUsed by CPU", multiplier=1)
multiply_by_disk = MultiplySizeDisk(
    name="Multiply TimeUsed by Disk", multiplier=1)

half_usage_by_ram = MultiplySizeRAM(
    name="Multiply TimeUsed by 50% of Ram (GB)", multiplier=.5*(1/1024))
half_usage_by_cpu = MultiplySizeCPU(
    name="Multiply TimeUsed by 50% of CPU", multiplier=.5)
half_usage_by_disk = MultiplySizeDisk(
    name="Multiply TimeUsed by 50% of Disk", multiplier=.5)

zero_burn_rate = MultiplyBurnTime(
    name="Stop all Total Time Used", multiplier=0.0)
half_burn_rate = MultiplyBurnTime(
    name="Half-Off Total Time Used", multiplier=0.5)
double_burn_rate = MultiplyBurnTime(
    name="Double Total Time Used", multiplier=2.0)

ignore_inactive = IgnoreStatusRule(
    "Ignore Inactive Instances",
    value=["build", "pending", "hard_reboot", "reboot", "migrating", "rescue",
           "resize", "verify_resize", "shutoff", "shutting-down", "suspended",
           "terminated", "deleted", "error", "unknown", "N/A", ])

ignore_suspended = IgnoreStatusRule("Ignore Suspended Instances", "suspended")
ignore_build = IgnoreStatusRule("Ignore 'Build' Instances", "build")


class InstanceHelper(object):
    def __init__(self, provider="openstack", machine="machine1"):
        if provider not in AVAILABLE_PROVIDERS:
            raise Exception(
                "The test provider specified is not a valid provider")

        if machine not in AVAILABLE_MACHINES:
            raise Exception(
                "The test machine specified is not a valid machine")

        self.provider = AVAILABLE_PROVIDERS[provider]
        self.machine = AVAILABLE_MACHINES[machine]
        self.history = []

    def add_history_entry(self, start, end, size="test.tiny",
                          status="active"):
        """
        Add a new history entry to the instance
        """
        if size not in AVAILABLE_SIZES:
            raise Exception("The test size specified is not a valid size")

        if status not in STATUS_CHOICES:
            raise Exception("The test status specified is not a valid status")

        new_history = InstanceHistory(
            status=status,
            size=AVAILABLE_SIZES[size],
            start_date=start,
            end_date=end)

        self.history.append(new_history)

    def to_instance(self, identifier):
        """
        Returns a new Instance
        or `raises` an Exception if the instance has no history
        """
        if not self.history:
            raise Exception(
                "This instance requires at least one history entry.")

        return Instance(
            identifier=identifier,
            provider=self.provider,
            machine=self.machine,
            history=self.history)


class AllocationHelper(object):
    def __init__(self, start_window, end_window, increase_date,
                 credit_hours=1000):
        self.start_window = start_window
        self.end_window = end_window
        self.instances = []

        # Add default credits
        self.credits = [
            AllocationIncrease(
                name="Add %s Hours " % credit_hours,
                unit=TimeUnit.hour,
                amount=credit_hours,
                increase_date=increase_date)
        ]

        # Add a default set of rules
        self.rules = [
            multiply_by_cpu,
            ignore_suspended,
            ignore_build,
            carry_forward
        ]

    def set_window(self, start_window, end_window):
        self.start_window = start_window
        self.end_window = end_window

    def add_instance(self, instance):
        if not isinstance(instance, Instance):
            raise TypeError("Expected type Instance got %s" % type(instance))

        self.instances.append(instance)

    def add_rule(self, rule):
        if not isinstance(rule, Rule):
            raise TypeError("Expected type Rule got %s" % type(rule))

        self.rules.append(rule)

    def add_credit(self, credit):
        if not isinstance(credit, AllocationIncrease):
            raise TypeError(
                "Expected type AllocationIncrease got %s" % type(credit))

        self.credits.append(credit)

    def to_allocation(self):
        """
        Returns a new allocation
        """
        return Allocation(
            credits=self.credits,
            rules=self.rules,
            instances=self.instances,
            start_date=self.start_window,
            end_date=self.end_window,
            interval_delta=None)


class AllocationTestCase(unittest.TestCase):
    def _calculate_allocation(self, allocation):
        """
        Returns the allocation result
        """
        return engine.calculate_allocation(allocation)

    def assertOverAllocation(self, allocation):
        """
        Assert that the allocation is over allocation
        """
        allocation_result = self._calculate_allocation(allocation)
        self.assertTrue(allocation_result.over_allocation())
        return self

    def assertCreditEquals(self, allocation, credit):
        """
        Assert that the remaining credit matches for the allocation
        """
        allocation_result = self._calculate_allocation(allocation)
        self.assertEqual(allocation_result.total_credit(), credit)
        return self

    def assertTotalRuntimeEquals(self, allocation, total_runtime):
        """
        Assert that the total runtime matches the allocation
        """
        allocation_result = self._calculate_allocation(allocation)
        self.assertEqual(allocation_result.total_runtime(), total_runtime)
        return self

    def assertDifferenceEquals(self, allocation, difference):
        """
        Assert that the difference and the allocation matches
        """
        allocation_result = self._calculate_allocation(allocation)
        self.assertEquals(allocation_result, difference)
        return self


def create_allocation(increase_date, start_window=None, end_window=None):
    """
    Returns an allocation
    Shortcut convience method to quickly create an allocation for testing.
    """

    # Initialize an allocation helper
    allocation_helper = AllocationHelper(start_window, end_window,
                                         increase_date)

    # Initialize an instance helper
    instance1_helper = InstanceHelper()

    # Set instance history
    history_start = datetime(2014, 7, 4, hour=12, tzinfo=pytz.utc)
    history_stop = datetime(2014, 12, 4, hour=12, tzinfo=pytz.utc)
    instance1_helper.add_history_entry(history_start, history_stop)

    instance1 = instance1_helper.to_instance("Test instance 1")

    allocation_helper.add_instance(instance1)

    return allocation_helper.to_allocation()


# Dynamic Tests
def test_instances(instance_ids, window_start, window_stop, credits=[],
                   rules=[]):
    """
    """
    instance_list = []
    for instance_id in instance_ids:
        core_instance = CoreInstance.objects.get(provider_alias=instance_id)
        instance_list.append(Instance.from_core(core_instance))
    return test_allocation(credits, rules, instance_list, window_start,
                           window_stop, interval_delta=None)


# Helper Tests
def create_allocation_test(
        window_start, window_stop,
        history_start, history_stop,
        credits, rules,
        swap_days=None, count=None, interval_date=None):
    """
    Create your own allocation test!
    Define a window (two datetimes)!
    Create a (Lot of) instance(s) and history!
    PASS IN your rules and credits!
    Swap between inactive/active status (If you want)!
    Create >1 instance with count!
    Set your own TimePeriod interval!
    """
    instances = instance_swap_status_test(
        history_start, history_stop, swap_days,
        size=medium_size, count=count)
    result = test_allocation(credits, rules, instances,
                             window_start, window_stop, interval_date)
    return result


def test_allocation(credits, rules, instances,
                    window_start, window_stop, interval_delta=None):
    allocation_input = Allocation(
        credits=credits,
        rules=rules,
        instances=instances,
        start_date=window_start, end_date=window_stop,
        interval_delta=interval_delta
    )
    allocation_result = calculate_allocation(allocation_input)
    return allocation_result


def instance_swap_status_test(history_start, history_stop, swap_days,
                              provider=None, machine=None, size=None, count=1):
    """
    Instance swaps from active/suspended every swap_days,
    Starting 'active' on history_start
    """
    history_list = _build_history_list(
        history_start, history_stop,
        ["active", "suspended"], tiny_size, timedelta(3))

    if not provider:
        provider = openstack
    if not machine:
        machine = random_machine
    instances = []

    # IDX 1
    for idx in xrange(1, count + 1):
        instance = Instance(
            identifier="Test-Instance-%s" % idx,
            provider=provider, machine=machine,
            history=history_list)
        instances.append(instance)
    return instances


def _build_history_list(history_start, history_stop, status_choices=[],
                        size=None,  swap_days=None):
    history_list = []

    #Good defaults:
    if not status_choices:
        status_choices = ["active", "suspended"]
    if not size:
        size = tiny_size
    if not swap_days:
        # Will be 'active' status, full history on defaults.
        new_history = InstanceHistory(
            status=status_choices[0], size=size,
            start_date=history_start,
            end_date=history_start+swap_days)
        return new_history

    history_next = history_start + swap_days
    next_idx = 0
    status_len = len(status_choices)
    while history_next < history_stop:
        status_choice = status_choices[next_idx]
        next_idx = (next_idx + 1) % status_len
        new_history = InstanceHistory(
            status=status_choice, size=size,
            start_date=history_start,
            end_date=history_start+swap_days)
        history_list.append(new_history)
        #Toggle/Update..
        history_start = history_next
        history_next += swap_days
    return history_list


class TestValidateInterval(TestCase):
    def setUp(self):
        self.start_time = datetime(2014, 7, 1, tzinfo=pytz.utc)
        self.end_time = datetime(2014, 7, 1, tzinfo=pytz.utc)
        self.start_time_missing_timezone = datetime(2014, 7, 1)
        self.end_time_missing_timezone = datetime(2014, 12, 1)

    def test_valid_allocation_times(self):
        """
        Given valid date range return an Allocation
        """
        self.assertTrue(validate_interval(self.start_time, self.end_time))

    def test_invalid_allocation_start_time(self):
        """
        When `start_time` has no timezone `raise` an Exception
        """
        params = (self.start_time_missing_timezone, self.end_time,)

        with self.assertRaises(Exception):
            validate_interval(*params)

        self.assertFalse(validate_interval(*params, raise_exception=False))

    def test_invalid_allocation_end_time(self):
        """
        When `end_time` has no timezone `raise` an Exception
        """
        params = (self.start_time, self.end_time_missing_timezone,)

        with self.assertRaises(Exception):
            validate_interval(*params)

        self.assertFalse(validate_interval(*params, raise_exception=False))


class TestEngineHelpers(unittest.TestCase):

    def setUp(self):
        # Set allocation window
        self.increase_date = datetime(2014, 7, 1, tzinfo=pytz.utc)
        self.start_window = datetime(2014, 7, 1, tzinfo=pytz.utc)
        self.end_window = datetime(2014, 12, 1, tzinfo=pytz.utc)

    def test_get_zero_date_time_is_valid(self):
        """
        Assert that the date time is utc timezone
        """
        zero_datetime = engine._get_zero_date_utc()

        # Validate that the time corresponds to the desired result
        self.assertEqual(zero_datetime.tzinfo, pytz.UTC)
        self.assertEqual(zero_datetime.year, 1970)
        self.assertEqual(zero_datetime.month, 1)
        self.assertEqual(zero_datetime.day, 1)
        self.assertEqual(zero_datetime.hour, 0)
        self.assertEqual(zero_datetime.minute, 0)
        self.assertEqual(zero_datetime.second, 0)

    def test_window_start_date_matches_allocation(self):
        """
        Assert that the window start_date matches the allocation.start_date
        """
        # Create allocation with a specific start_date and no end_date
        allocation = create_allocation(
            self.increase_date, start_window=self.start_window)
        (start, end) = engine.get_allocation_window(allocation)
        self.assertEqual(start, self.start_window)

    def test_window_end_date_matches_allocation(self):
        """
        Assert that the window end_date matches the allocation.end_date
        """
        # Create allocation with no start_date and with a specific end date
        allocation = create_allocation(
            self.increase_date, end_window=self.end_window)
        (start, end) = engine.get_allocation_window(allocation)
        self.assertEqual(end, self.end_window)

    def test_window_matches_default_window(self):
        """
        Assert that the window matches the default window
        """
        # Create allocation with no start_date and no end_date
        allocation = create_allocation(self.increase_date)
        end_date = datetime(1990, 1, 1, tzinfo=pytz.utc)

        # Override the default end date to a testable value
        (start, end) = engine.get_allocation_window(
            allocation, default_end_date=end_date)

        self.assertEquals(start, engine._get_zero_date_utc())
        self.assertEquals(end, end_date)


class TestAllocationEngine(AllocationTestCase):
    def setUp(self):
        # Set allocation window
        increase_date = start_window = datetime(2014, 7, 1, tzinfo=pytz.utc)
        stop_window = datetime(2014, 12, 1, tzinfo=pytz.utc)

        # Initialize allocation helper
        self.allocation_helper = AllocationHelper(start_window, stop_window,
                                                  increase_date)
        # Initialize instance helper
        self.instance1_helper = InstanceHelper()

    def test_total_credit_matches(self):
        """
        Allocation should have 10,000 credit hours
        """
        allocation = self.allocation_helper.to_allocation()
        self.assertCreditEquals(allocation, timedelta(hours=1000))

    def test_over_allocation(self):
        """
        Returns True
        When the total allocation time exceeds the total total runtime
        """
        history_start = datetime(2014, 7, 4, hour=12, tzinfo=pytz.utc)
        history_stop = datetime(2014, 12, 4, hour=12, tzinfo=pytz.utc)
        self.instance1_helper.add_history_entry(history_start, history_stop)
        instance1 = self.instance1_helper.to_instance("Test instance 1")

        self.allocation_helper.add_instance(instance1)
        allocation = self.allocation_helper.to_allocation()
        self.assertOverAllocation(allocation)

    @unittest.skip("Finish writing test")
    def test_over_allocation_boundary_condition(self):
        """
        Returns True
        When the total allocation time is equal to the total runtime
        """
        start_window = datetime(2014, 5, 1, tzinfo=pytz.utc)
        stop_window = datetime(2014, 5, 10, tzinfo=pytz.utc)

        self.allocation_helper = AllocationHelper(
            start_window, stop_window, credit_hours=240)

    @unittest.skip("Finish writing test")
    def test_under_allocation(self):
        """
        Returns False
        When the total allocation time has not been exceeded.
        """
        #history_start = datetime(2014, 7, 4, hour=12, tzinfo=pytz.utc)
        #history_stop = datetime(2014, 12, 4, hour=12, tzinfo=pytz.utc)

    def test_allocation_for_multiple_instances(self):
        """
        Checks that the sum of allocations meets the expected value
        """
        current_time = datetime(2014, 7, 4, hour=12, tzinfo=pytz.utc)

        # Create 10 instances of uniform size
        for idx in range(0, 10):
            start_time = current_time
            current_time = end_time = current_time + timedelta(days=3)

            helper = InstanceHelper()

            # Add 3 days of active
            helper.add_history_entry(start_time, end_time)

            # Add 3 days of suspended following active time
            helper.add_history_entry(end_time, end_time + timedelta(days=3),
                                     status="suspended")

            self.allocation_helper.add_instance(
                helper.to_instance("Instance %s" % idx))

        allocation = self.allocation_helper.to_allocation()
        self.assertTotalRuntimeEquals(allocation, timedelta(days=30))

    def test_allocation_for_multiple_instance_sizes(self):
        start_time = datetime(2014, 7, 4, hour=12, tzinfo=pytz.utc)
        end_time = start_time + timedelta(days=3)
        sizes = ["test.tiny", "test.small", "test.medium", "test.large"]

        for size in sizes:
            helper = InstanceHelper()

            # Add 3 days of active
            helper.add_history_entry(start_time, end_time, size=size)

            # Add 3 days of suspended following active time
            helper.add_history_entry(
                end_time, end_time + timedelta(days=3),
                status="suspended", size=size)

            self.allocation_helper.add_instance(
                helper.to_instance("Instance %s" % size))

        allocation = self.allocation_helper.to_allocation()
        self.assertTotalRuntimeEquals(allocation, timedelta(days=45))

# Static tests
def run_test_1():
    """
    Test 1:
    Window set at 5 months (7/1/14 - 12/1/14)
    One-time credit of 10,000 AU (7/1)
    One instance running for ~5 months (Not quite because of 3-day offset)
    Assertions:
    When Dividing time into three different intervals:
    (Cumulative, Monthly+Rollover, n-days+Rollover)
    * allocation_credit, total_runtime(), and total_difference() are IDENTICAL.
      (NO TIME LOSS)
    """
    # Allocation Window
    window_start = datetime(2014, 7, 1, tzinfo=pytz.utc)
    window_stop = datetime(2014, 12, 1, tzinfo=pytz.utc)

    # Instances
    count = 1
    swap_days = timedelta(3)
    history_start = datetime(2014, 7, 4, hour=12, tzinfo=pytz.utc)
    history_stop = datetime(2014, 12, 4, hour=12, tzinfo=pytz.utc)

    # Allocation Credits
    achieve_greatness = AllocationIncrease(
        name="Add 10,000 Hours ",
        unit=TimeUnit.hour, amount=10000,
        increase_date=window_start)
    credits = [achieve_greatness]

    rules = [multiply_by_cpu, ignore_suspended, ignore_build, carry_forward]

    interval_days = None
    print "Running Cumulative Test"
    result_1 = create_allocation_test(
        window_start, window_stop, history_start,
        history_stop, credits, rules, swap_days, count, interval_days)

    print "Running timedelta Test"
    interval_days = timedelta(21)
    result_2 = create_allocation_test(
        window_start, window_stop, history_start,
        history_stop, credits, rules, swap_days, count, interval_days)

    print "Running relativedelta Test"
    interval_days = relativedelta(day=1, months=1)
    result_3 = create_allocation_test(
        window_start, window_stop, history_start,
        history_stop, credits, rules, swap_days, count, interval_days)

    test_1 = result_1.over_allocation()
    test_2 = result_2.over_allocation()
    test_3 = result_3.over_allocation()
    if test_1 != test_2 != test_3:
        raise Exception("Mismatch on Over-Allocation Result: "
                        "Cumulative:%s Timedelta:%s Relativedelta:%s"
                        % (test_1, test_2, test_3))

    test_1 = result_1.total_runtime()
    test_2 = result_2.total_runtime()
    test_3 = result_3.total_runtime()
    if test_1 != test_2 != test_3:
        raise Exception("Mismatch on Total Runtime: "
                        "Cumulative:%s Timedelta:%s Relativedelta:%s"
                        % (test_1, test_2, test_3))

    test_1 = result_1.total_credit()
    test_2 = result_2.total_credit()
    test_3 = result_3.total_credit()
    if test_1 != test_2 != test_3:
        raise Exception("Mismatch on Total Allocation Credit Received: "
                        "Cumulative:%s Timedelta:%s Relativedelta:%s"
                        % (test_1, test_2, test_3))

    test_1 = result_1.total_difference()
    test_2 = result_2.total_difference()
    test_3 = result_3.total_difference()
    if test_1 != test_2 != test_3:
        raise Exception("Mismatch on Total Allocation: "
                        "Cumulative:%s Timedelta:%s Relativedelta:%s"
                        % (test_1, test_2, test_3))
    return True


def run_test2():
    """
    TODO: Setup some new constraints here..
    """
    # Allocation Window
    window_start = datetime(2014, 7, 1, tzinfo=pytz.utc)
    window_stop = datetime(2014, 12, 1, tzinfo=pytz.utc)

    # Instances
    swap_days = timedelta(3)
    history_start = datetime(2014, 7, 4, hour=12, tzinfo=pytz.utc)
    history_stop = datetime(2014, 12, 4, hour=12, tzinfo=pytz.utc)

    # Allocation Credits
    achieve_greatness = AllocationIncrease(
        name="Add 10,000 Hours ",
        unit=TimeUnit.hour, amount=10000,
        increase_date=window_start)

    instances = instance_swap_status_test(
        history_start, history_stop, swap_days,
        size=medium_size, count=1)

    credits = [achieve_greatness]

    rules = [multiply_by_cpu, ignore_suspended, ignore_build]

    result = test_allocation(credits, rules, instances,
                             window_start, window_stop, None)
    return result

"""
Examples I think will break things:
    1. start_date = 1/1, end_date = 1/31
    2. Instances use 7 days of allocation from 1/1 to 1/8
    3. User has his monthly allocation on 1/8 (14 days)
    4. Instances use 7 days of allocation from 1/8 to 1/15
Questions:
    2. What "AllocationIncreases" are valid if the dates occur PRIOR to the
    recharge_date?
       * I think they should be ignored, and given a new AllocationIncrease
       * with the remainder value (The amount of that increase used in the
       * month PRIOR).
    # Should step 2 be allowed in the engine, should invalid time periods flag
    # in some way??
"""
