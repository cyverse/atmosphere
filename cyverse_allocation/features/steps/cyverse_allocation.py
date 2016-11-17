from behave import *
from cyverse_allocation.spoof_instance import UserWorkflow,create_allocation_source
from dateutil.parser import parse
from datetime import timedelta

@given('we create a new user')
def step_impl(context):
    context.user1 = UserWorkflow()

@when('we create and assign an allocation source to user')
def step_impl(context):
    ts = parse('2016-10-04T00:00+00:00')
    allocation_source = create_allocation_source(name='TestSource', compute_allowed=1000, timestamp=ts)
    context.user1.assign_allocation_source_to_user(allocation_source, timestamp=ts + timedelta(minutes=10))

@then('user should have an allocation source')
def step_impl(context):
    assert context.user1.is_allocation_source_assigned()
