from behave import *
from cyverse_allocation.spoof_instance import UserWorkflow,create_allocation_source
from dateutil.parser import parse
from datetime import timedelta
from core.models.allocation_source import total_usage
from core.models.event_table import EventTable
from core.models.allocation_source import AllocationSourceSnapshot
from cyverse_allocation.cyverse_rules_engine_setup import CyverseTestRenewalVariables, CyverseTestRenewalActions,cyverse_rules
from business_rules import run_all


# run_all(rule_list=cyverse_rules,
# defined_variables=CyverseTestRenewalVariables(allocation_source,current_time),
# defined_actions=CyverseTestRenewalActions(allocation_source,current_time),
# )

# scenario 1

@given('we create a new user, Amit')
def step_impl(context):
    context.amit = UserWorkflow()

@when('we create and assign an allocation source TestAllocationSource with default renewal to Amit')
def step_impl(context):
    context.ts = parse('2016-10-04T00:00+00:00')
    context.allocation_source_1 = create_allocation_source(name='TestSource', compute_allowed=1000, timestamp=context.ts)
    context.amit.assign_allocation_source_to_user(context.allocation_source_1, timestamp=context.ts)

@then('Amit should have the allocation source TestAllocationSource')
def step_impl(context):
    assert context.amit.is_allocation_source_assigned_to_user()


# scenario 2

@given('Amit creates an instance')
def step_impl(context):
    # instance created after 10 minutes of assigning an allocation source
    context.execute_steps(
        u'''
        Given we create a new user, Amit
        when we create and assign an allocation source TestAllocationSource with default renewal to Amit
        then Amit should have the allocation source TestAllocationSource
        ''')
    context.amit_instance_1 = context.amit.create_instance(start_date=context.ts)

@when('Amits instance runs for 2 hours')
def step_impl(context):
    context.amit.create_instance_status_history(context.amit_instance_1, start_date=context.ts + timedelta(hours=2), status='suspend')

@then('the total usage on TestAllocationSource is 0 hours')
def step_impl(context):
    report_start_date = context.ts
    report_end_date = context.ts + timedelta(minutes=120)
    tots = total_usage(context.amit.user.username, report_start_date, allocation_source_name=context.allocation_source_1.name,
                end_date=report_end_date)
    print(tots)
    assert total_usage(context.amit.user.username, report_start_date, allocation_source_name=context.allocation_source_1.name,
                end_date=report_end_date)==0.0


# scenario 3

@given('Amit assigns instance to TestAllocationSource')
def step_impl(context):
    # instance created after 10 minutes of assigning an allocation source
    context.execute_steps(
        u'''
        Given we create a new user, Amit
        when we create and assign an allocation source TestAllocationSource with default renewal to Amit
        then Amit should have the allocation source TestAllocationSource
        Given Amit creates an instance
        when Amits instance runs for 2 hours
        then the total usage on TestAllocationSource is 0 hours
        ''')
    context.amit.assign_allocation_source_to_instance(context.allocation_source_1, context.amit_instance_1,
                                                      timestamp=context.ts + timedelta(hours=2))
    context.amit.create_instance_status_history(context.amit_instance_1,
                                                start_date=context.ts + timedelta(hours=2),
                                                status='active')

@when('Amits instance runs for another 2 hours')
def step_impl(context):
    context.amit.create_instance_status_history(context.amit_instance_1,
                                                start_date=context.ts + timedelta(hours=4),
                                                status='suspended')

@then('the total usage on TestAllocationSource is 2 hours')
def step_impl(context):
    report_start_date = context.ts
    report_end_date = context.ts + timedelta(hours=4)
    assert total_usage(context.amit.user.username, report_start_date, allocation_source_name=context.allocation_source_1.name,
                end_date=report_end_date)==2.0


# scenario 4

@given('we create user, Julian and assign him to TestAllocationSource 1 hour after Amit is assigned')
def step_impl(context):
    # instance created after 10 minutes of assigning an allocation source
    context.execute_steps(
        u'''
        Given we create a new user, Amit
        when we create and assign an allocation source TestAllocationSource with default renewal to Amit
        then Amit should have the allocation source TestAllocationSource
        Given Amit creates an instance
        when Amits instance runs for 2 hours
        then the total usage on TestAllocationSource is 0 hours
        Given Amit assigns instance to TestAllocationSource
        when Amits instance runs for another 2 hours
        then the total usage on TestAllocationSource is 2 hours
        ''')

    context.julian = UserWorkflow()
    context.julian.assign_allocation_source_to_user(context.allocation_source_1, timestamp=context.ts+timedelta(hours=1))


@when('Julian launches an instance on TestAllocationSource and runs it for 3 hours')
def step_impl(context):
    context.julian_instance_1 = context.julian.create_instance(start_date=context.ts+timedelta(hours=1))
    context.julian.assign_allocation_source_to_instance(context.allocation_source_1, context.julian_instance_1,
                                                      timestamp=context.ts + timedelta(hours=1))
    context.julian.create_instance_status_history(context.julian_instance_1,
                                                start_date=context.ts + timedelta(hours=4),
                                                status='suspended')


@then('the total usage on TestAllocationSource source is 5 hours')
def step_impl(context):
    report_start_date = context.ts
    report_end_date = context.ts + timedelta(hours=4)
    tots = total_usage(context.julian.user.username, report_start_date, allocation_source_name=context.allocation_source_1.name,
                end_date=report_end_date) + total_usage(context.amit.user.username, report_start_date, allocation_source_name=context.allocation_source_1.name,
                end_date=report_end_date)
    assert tots == 5.0


# scenario 5

@given('default settings')
def step_impl(context):
    context.execute_steps(
        u'''
        Given we create a new user, Amit
        when we create and assign an allocation source TestAllocationSource with default renewal to Amit
        then Amit should have the allocation source TestAllocationSource
        Given Amit creates an instance
        when Amits instance runs for 2 hours
        then the total usage on TestAllocationSource is 0 hours
        Given Amit assigns instance to TestAllocationSource
        when Amits instance runs for another 2 hours
        then the total usage on TestAllocationSource is 2 hours
        Given we create user, Julian and assign him to TestAllocationSource 1 hour after Amit is assigned
        when Julian launches an instance on TestAllocationSource and runs it for 3 hours
        then the total usage on TestAllocationSource source is 5 hours
        ''')

@when('new allocation source DefaultAllocationSource is created with compute allowed 128')
def step_impl(context):
    context.allocation_source_2 = create_allocation_source(name='DefaultAllocationSource', compute_allowed=128,
                                                           timestamp=context.ts)

@then('allocation_source_created event is fired for DefaultAllocationSource')
def step_impl(context):
    context.query = EventTable.objects.filter(name='allocation_source_created', payload__name__exact='DefaultAllocationSource')
    assert len(context.query)==1

@then('renewal_strategy for allocation source is default')
def step_impl(context):
    assert context.query.last().payload['renewal_strategy']=='default'


# scenario 6

@given('Amit is assigned to DefaultAllocationSource')
def step_impl(context):
    context.execute_steps(
        u'''
        Given we create a new user, Amit
        when we create and assign an allocation source TestAllocationSource with default renewal to Amit
        then Amit should have the allocation source TestAllocationSource
        Given Amit creates an instance
        when Amits instance runs for 2 hours
        then the total usage on TestAllocationSource is 0 hours
        Given Amit assigns instance to TestAllocationSource
        when Amits instance runs for another 2 hours
        then the total usage on TestAllocationSource is 2 hours
        Given we create user, Julian and assign him to TestAllocationSource 1 hour after Amit is assigned
        when Julian launches an instance on TestAllocationSource and runs it for 3 hours
        then the total usage on TestAllocationSource source is 5 hours
        Given default settings
        when new allocation source DefaultAllocationSource is created with compute allowed 128
        ''')

    context.amit.assign_allocation_source_to_user(context.allocation_source_2,
                                                    timestamp=context.ts)

@when('Amit runs an instance on DefaultAllocationSource for 3 days')
def step_impl(context):
    context.amit_instance_2 = context.amit.create_instance(start_date=context.ts)
    context.amit.assign_allocation_source_to_instance(context.allocation_source_2, context.amit_instance_2,
                                                      timestamp=context.ts)

    context.amit.create_instance_status_history(context.amit_instance_2,
                                                start_date=context.ts + timedelta(days=3),
                                                status='suspend')


@then('renewal event is fired after 1 month for DefaultAllocationSource')
def step_impl(context):
    # after 1 month , AllocationSourceSnapshot is first updated.

    report_start_date = context.ts
    report_end_date = context.ts + timedelta(days=30)
    query = EventTable.objects.filter(name='allocation_source_renewed',
                                              payload__name__exact='DefaultAllocationSource')
    assert len(query) == 0
    source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=context.allocation_source_2).order_by('updated').last()
    assert total_usage(context.amit.user.username, report_start_date, allocation_source_name=context.allocation_source_2.name,
                end_date=report_end_date) == 72.0
    source_snapshot.compute_used = total_usage(context.amit.user.username, report_start_date, allocation_source_name=context.allocation_source_2.name,
                end_date=report_end_date)
    source_snapshot.updated = context.ts + timedelta(days=29)
    source_snapshot.save()

    assert AllocationSourceSnapshot.objects.filter(allocation_source=context.allocation_source_2).order_by('updated').last().compute_used == 72.0

    # rules engine is explicitly run

    current_time = context.ts + timedelta(days=30)
    run_all(rule_list=cyverse_rules,
    defined_variables=CyverseTestRenewalVariables(context.allocation_source_2,current_time),
    defined_actions=CyverseTestRenewalActions(context.allocation_source_2,current_time),
    )

    query = EventTable.objects.filter(name='allocation_source_renewed', payload__name__exact='DefaultAllocationSource')
    assert len(query)==1

@then('compute_allowed on the 30th day is 184 after the carry over')
def step_impl(context):
    source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=context.allocation_source_2).last()
    assert source_snapshot.compute_allowed == 128
