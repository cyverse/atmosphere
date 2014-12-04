from django.test import TestCase
from django.utils.timezone import datetime
# Create your tests here.

from allocation.engine import calculate_allocation
from allocation.models import Allocation, Rule, Instance, InstanceHistory,\
                              Size, InstanceResult
#Timezone-aware datetimes
nov_1 = datetime(2014,11,1)
nov_8 = datetime(2014,11,8)
nov_15 = datetime(2014,11,15)
nov_16 = datetime(2014,11,16)
nov_31 = datetime(2014,11,31)
dec_1 = datetime(2014,12,1)
dec_4 = datetime(2014,12,4)

#Objects

openstack = Provider(
        name="iPlant Cloud - Tucson",
        identifier="4")

random_machine = Machine(
        name="Not real machine",
        identifier="39966e54-9282-4fc8-bc13-10b03d616c54")

tiny_size = Size(id='test.tiny', cpu=1, ram=1024*2, disk=0)
small_size = Size(id='test.small', cpu=2, ram=1024*8, disk=60)
medium_size = Size(id='test.medium', cpu=4, ram=1024*16, disk=120)
large_size = Size(id='test.large', cpu=8, ram=1024*32, disk=240)

history_1 = InstanceHistory(
     start_date=nov_1, end_date=nov_15,
     size=tiny_size, status="active")
history_2 = InstanceHistory(
     start_date=nov_15, end_date=nov_16,
     size=tiny_size, status="suspended")
history_3 = InstanceHistory(
     start_date=nov_16, end_date=dec_4,
     size=tiny_size, status="active")
history_4 = InstanceHistory(start_date=nov_1, end_date=nov_8,
     size=small_size, status="active")
history_5 = InstanceHistory(start_date=nov_8, end_date=nov_15,
     size=small_size, status="suspended")
history_6 = InstanceHistory(start_date=nov_15, end_date=dec_4,
     size=tiny_size, status="active")

instance_30days = Instance(
        identifier="TestInst-ance-Equa-ls__-33Days__1234",
        machine=random_machine, provider=openstack,
        history=[history_1, history_2, history_3])
instance_35days = Instance(
        identifier="TestInst-ance-Equa-ls__-34Days__1234",
        machine=random_machine, provider=openstack,
        history=[history_4, history_5, history_6])

# Rules

multiply_by_ram =  MultiplySizeRAM(
        name="Multiply TimeUsed by Ram", amount=(1/1024))
multiply_by_cpu =  MultiplySizeCPU(
        name="Multiply TimeUsed by CPU", amount=1)
multiply_by_disk = MultiplySizeDisk(
        name="Multiply TimeUsed by Disk", amount=1)

half_usage_by_ram =  MultiplySizeRAM(
        name="Multiply TimeUsed by 50% of Ram",
        amount=.5*(1/1024) )
half_usage_by_cpu =  MultiplySizeCPU(
        name="Multiply TimeUsed by 50% of CPU",
        amount=.5)
half_usage_by_disk = MultiplySizeDisk(
        name="Multiply TimeUsed by 50% of Disk",
        amount=.5)

half_burn_rate = MultiplyBurnTime(name="Half-Off Total Time Used", amount=0.5)
double_burn_rate = MultiplyBurnTime(name="Double Total Time Used", amount=2.0)

add_50_hours =    AllocationIncrease(name="Add 50 Hours", unit=TimeUnit.hour, amount=50)
add_500_hours =   AllocationIncrease(name="Add 500 Hours", unit=TimeUnit.hour, amount=500)
two_free_months = AllocationIncrease(name="Add Two Months", unit=TimeUnit.month, amount=2)

normal_recharge = AllocationRecharge(
        name="One Month of time starting on December 1st",
        unit="month", amount=1, recharge_date=dec_1)
half_recharge = AllocationRecharge(
        name="Add 1/2 Month of time starting on November 1st",
        unit="month", amount=0.5, recharge_date=nov_1)

allocation_test_1 = Allocation(
    rules=[normal_recharge, multiply_by_cpu, ignore_suspended],
    instances=[instance_30days, instance_35days],
    start_date=nov_1,
    end_date=nov_31
)
allocation_test_2 = Allocation(
    rules=[normal_recharge, multiply_by_cpu],
    instances=[instance_30days, instance_35days],
    start_date=nov_1,
    end_date=nov_31
)

allocation_result = calculate_allocation(allocation_test_1)
print allocation_result
allocation_result = calculate_allocation(allocation_test_2)
print allocation_result

