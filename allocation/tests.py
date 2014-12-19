from allocation import engine
from allocation.models import Provider, Machine, Size, Instance, InstanceHistory
from core.models import Instance as CoreInstance
from allocation.models import Allocation,\
        MultiplySizeCPU, MultiplySizeRAM,\
        MultiplySizeDisk, MultiplyBurnTime,\
        AllocationIncrease, AllocationRecharge, TimeUnit,\
        IgnoreStatusRule, CarryForwardTime, validate_interval
from django.test import TestCase
from django.utils import unittest
from django.utils.timezone import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz

#For testing..


openstack = Provider(
        name="iPlant Cloud - Tucson",
        identifier="4")
openstack_workshop = Provider(
        name="iPlant Cloud Workshop - Tucson",
        identifier="5")
random_machine = Machine(
        name="Not real machine",
        identifier="12412515-1241-3fc8-bc13-10b03d616c54")
random_machine_2 = Machine(
        name="Not real machine",
        identifier="39966e54-9282-4fc8-bc13-10b03d616c54")
tiny_size = Size(name='Kids Fry', identifier='test.tiny', cpu=1, ram=1024*2, disk=0)
small_size = Size(name='Small Fry', identifier='test.small', cpu=2, ram=1024*4, disk=60)
medium_size = Size(name='Medium Fry', identifier='test.medium', cpu=4, ram=1024*16, disk=120)
large_size = Size(name='Large Fry', identifier='test.large', cpu=8, ram=1024*32, disk=240)
# Rules
carry_forward = CarryForwardTime()

multiply_by_ram = MultiplySizeRAM(
        name="Multiply TimeUsed by Ram (*1GB)", multiplier=(1/1024))
multiply_by_cpu = MultiplySizeCPU(
        name="Multiply TimeUsed by CPU", multiplier=1)
multiply_by_disk = MultiplySizeDisk(
        name="Multiply TimeUsed by Disk", multiplier=1)

half_usage_by_ram = MultiplySizeRAM(
        name="Multiply TimeUsed by 50% of Ram (GB)",
        multiplier=.5*(1/1024) )
half_usage_by_cpu =  MultiplySizeCPU(
        name="Multiply TimeUsed by 50% of CPU",
        multiplier=.5)
half_usage_by_disk = MultiplySizeDisk(
        name="Multiply TimeUsed by 50% of Disk",
        multiplier=.5)

zero_burn_rate = MultiplyBurnTime(name="Stop all Total Time Used", multiplier=0.0)
half_burn_rate = MultiplyBurnTime(name="Half-Off Total Time Used", multiplier=0.5)
double_burn_rate = MultiplyBurnTime(name="Double Total Time Used", multiplier=2.0)

ignore_inactive = IgnoreStatusRule("Ignore Inactive Instances", value=["build", "pending",
    "hard_reboot", "reboot",
     "migrating", "rescue",
     "resize", "verify_resize",
    "shutoff", "shutting-down",
    "suspended", "terminated",
    "deleted", "error", "unknown","N/A",
    ])
ignore_suspended = IgnoreStatusRule("Ignore Suspended Instances", "suspended")
ignore_build = IgnoreStatusRule("Ignore 'Build' Instances", "build")


#Dynamic Tests
def test_instances(instance_ids, window_start, window_stop, credits=[], rules=[]):
    """
    """
    instance_list = []
    for instance_id in instance_ids:
        core_instance = CoreInstance.objects.get(provider_alias=instance_id)
        instance_list.append(Instance.from_core(core_instance))
    return test_allocation(credits, rules, instance_list,
            window_start, window_stop, interval_delta=None)
#Helper Tests
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
    allocation_result = engine.calculate_allocation(allocation_input)
    return allocation_result

def instance_swap_status_test(history_start, history_stop, swap_days,
                              provider=None, machine=None, size=None, count=1):
    """
    Instance swaps from active/suspended every swap_days,
    Starting 'active' on history_start
    """
    history_list = _build_history_list(history_start, history_stop,
            ["active","suspended"], tiny_size, timedelta(3))
    if not provider:
        provider = openstack
    if not machine:
        machine = random_machine
    instances = []
    for idx in xrange(1,count+1):#IDX 1
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
        status_choices = ["active","suspended"]
    if not size:
        size = tiny_size
    if not swap_days:
        #Will be 'active' status, full history on defaults.
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
        self.start_time = datetime(2014,7,1, tzinfo=pytz.utc)
        self.end_time = datetime(2014,7,1, tzinfo=pytz.utc)
        self.start_time_missing_timezone = datetime(2014,7,1)
        self.end_time_missing_timezone = datetime(2014,12,1)

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


#Static tests
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
    #Allocation Window
    window_start = datetime(2014,7,1, tzinfo=pytz.utc)
    window_stop = datetime(2014,12,1, tzinfo=pytz.utc)
    #Instances
    count = 1
    swap_days = timedelta(3)
    history_start = datetime(2014,7,4,hour=12, tzinfo=pytz.utc)
    history_stop = datetime(2014,12,4,hour=12, tzinfo=pytz.utc)
    #Allocation Credits
    achieve_greatness = AllocationIncrease(
            name="Add 10,000 Hours ",
            unit=TimeUnit.hour, amount=10000,
            increase_date=window_start)
    credits = [achieve_greatness]

    rules = [multiply_by_cpu, ignore_suspended, ignore_build, carry_forward]

    interval_days = None
    print "Running Cumulative Test"
    result_1 = create_allocation_test(window_start, window_stop, history_start,
            history_stop, credits, rules, swap_days, count, interval_days)

    print "Running timedelta Test"
    interval_days = timedelta(21)
    result_2 = create_allocation_test(window_start, window_stop, history_start,
            history_stop, credits, rules, swap_days, count, interval_days)

    print "Running relativedelta Test"
    interval_days = relativedelta(day=1, months=1)
    result_3 = create_allocation_test(window_start, window_stop, history_start,
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
    #Allocation Window
    window_start = datetime(2014,7,1, tzinfo=pytz.utc)
    window_stop = datetime(2014,12,1, tzinfo=pytz.utc)
    #Instances
    swap_days = timedelta(3)
    history_start = datetime(2014,7,4,hour=12, tzinfo=pytz.utc)
    history_stop = datetime(2014,12,4,hour=12, tzinfo=pytz.utc)
    #Allocation Credits
    achieve_greatness = AllocationIncrease(
            name="Add 10,000 Hours ",
            unit=TimeUnit.hour, amount=10000,
            increase_date=window_start)

    instances = instance_swap_status_test(
            history_start, history_stop, swap_days,
            size=medium_size, count=1)
    credits=[achieve_greatness]
    rules=[multiply_by_cpu, ignore_suspended, ignore_build]
    result = test_allocation(credits, rules, instances,
            window_start, window_stop, interval_days)
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
