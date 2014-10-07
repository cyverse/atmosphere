from django.test import TestCase
# Create your tests here.

from allocation.engine import calculate_allocation
from allocation.models import Allocation, Rule, Instance, InstanceHistory,\
                              Size, InstanceResult
tiny_size = Size(id='test.tiny', cpu=1, ram=1024*2, disk=0)
small_size = Size(id='test.small', cpu=2, ram=1024*8, disk=60)
medium_size = Size(id='test.medium', cpu=4, ram=1024*16, disk=120)
large_size = Size(id='test.large', cpu=8, ram=1024*32, disk=240)

history_1 = InstanceHistory(
     start_date="2014-10-01T00:00:00Z", end_date="2014-10-15T00:00:00Z",
     size=tiny_size, status="active")
history_2 = InstanceHistory(
     start_date="2014-10-15T00:00:00Z", end_date="2014-10-16T00:00:00Z",
     size=tiny_size, status="suspended")
history_3 = InstanceHistory(
     start_date="2014-10-16T00:00:00Z", end_date="2014-11-01T00:00:00Z",
     size=tiny_size, status="active")
instance_30days = Instance(
        identifier="TestInst-ance-Equa-ls__-30Days__1234",
        machine="39966e54-9282-4fc8-bc13-10b03d616c54",
        provider=4, history=[history_1, history_2, history_3])

history_4 = InstanceHistory(
     start_date="2014-10-01T00:00:00Z", end_date="2014-10-08T00:00:00Z",
     size=small_size, status="active")
history_5 = InstanceHistory(
     start_date="2014-10-08T00:00:00Z", end_date="2014-10-15T00:00:00Z",
     size=small_size, status="suspended")
history_6 = InstanceHistory(
     start_date="2014-10-15T00:00:00Z", end_date="2014-11-01T00:00:00Z",
     size=tiny_size, status="active")
instance_35days = Instance(
        identifier="TestInst-ance-Equa-ls__-31Days__1234",
        machine="39966e54-9282-4fc8-bc13-10b03d616c54",
        provider=4, history=[history_4, history_5, history_6])

multiply_by_ram = Rule(name="Multiply TimeUsed by Ram", type="size_ram", amount=1)
multiply_by_cpu = Rule(name="Multiply TimeUsed by CPU", type="size_cpu", amount=1)
multiply_by_disk = Rule(name="Multiply TimeUsed by Disk", type="size_disk", amount=1)

ram_usage_half_off = Rule(name="Half-Off RAM", type="size_ram", amount=0.5)
cpu_usage_half_off = Rule(name="Half-Off CPU", type="size_cpu", amount=0.5)
disk_usage_half_off = Rule(name="Half-Off Disk", type="size_disk", amount=0.5)

half_burn_rate = Rule(name="Half-Off Time Used", type="burn_rate", amount=0.5)
double_burn_rate = Rule(name="Double Time Used", type="burn_rate", amount=2.0)

add_50_hours = Rule(name="Add 50 Hours", type="increase_allocation", unit="hour", amount=50)
add_500_hours = Rule(name="Add 500 Hours", type="increase_allocation", unit="hour", amount=500)
double_recharge = Rule(name="Add Two Months", type="increase_allocation", unit="month", amount=2)
normal_recharge = Rule(name="Add Month", type="increase_allocation", unit="month", amount=1)
half_recharge = Rule(name="Add 1/2 Month", type="increase_allocation", unit="month", amount=0.5)

allocation_test_1 = Allocation(
    rules=[normal_recharge, multiply_by_cpu],
    instances=[instance_30days, instance_35days],
    start_date="2014-10-01T00:00:00Z",
    end_date="2014-11-01T00:00:00Z"
)

allocation_result = calculate_allocation(allocation_test_1)
print allocation_result

