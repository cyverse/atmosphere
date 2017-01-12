from behave import *
from django.test.client import Client
from core.models import AtmosphereUser

@given('a user')
def step_impl(context):
    context.client = Client()
    # the only user who can access apis on dev is lenards, so set staff permission for lenards on test db
    user, not_created = AtmosphereUser.objects.get_or_create(username='lenards', password='lenards')
    if not_created:
        user.is_staff = True
        user.is_superuser = True
        user.save()
    context.client.login()

# Allocation Source Creation

@when('create_allocation_source command is fired')
def step_impl(context):
    for row in context.table:
        context.response = context.client.post('/api/v2/allocation_source_command',
                                               {"action": "create_allocation_source",
                                                "renewal_strategy": row['renewal strategy'],
                                                "name": row['name'],
                                                "compute_allowed": row['compute allowed']})

@then('allocation source is created = {allocation_source_is_created}')
def step_impl(context,allocation_source_is_created):
    result = True if context.response.status_code==201 else False
    assert result==_str2bool(allocation_source_is_created.lower())


# Change Renewal Event

@given('An Allocation Source with renewal strategy')
def step_impl(context):
    for row in context.table:
        allocation_source = context.client.post('/api/v2/allocation_source_command',
                                               {"action": "create_allocation_source",
                                                "renewal_strategy": row['renewal strategy'],
                                                "name": "TestAllocationSource",
                                                "compute_allowed": 5000})
        context.source_id = allocation_source.data['source_id']

@when('change_renewal_strategy command is fired with {new_renewal_strategy}')
def step_impl(context, new_renewal_strategy):
    context.response = context.client.post('/api/v2/allocation_source_command',
                                           {"action": "change_renewal_strategy",
                                            "source_id": context.source_id,
                                            "renewal_strategy": new_renewal_strategy})
    context.new_renewal_strategy = new_renewal_strategy

@then('renewal strategy is changed = {renewal_strategy_is_changed}')
def step_impl(context, renewal_strategy_is_changed):
    result = True if context.response.status_code == 201 else False
    if not result:
        assert result == _str2bool(renewal_strategy_is_changed.lower())
    else:
        assert result == _str2bool(renewal_strategy_is_changed.lower()) and context.response.data['renewal_strategy']==context.new_renewal_strategy


# Change Allocation Source Name

@given('An Allocation Source with name')
def step_impl(context):
    for row in context.table:
        allocation_source = context.client.post('/api/v2/allocation_source_command',
                                               {"action": "create_allocation_source",
                                                "renewal_strategy": 'default',
                                                "name": row["name"],
                                                "compute_allowed": 5000})

        context.source_id = allocation_source.data['source_id']

@when('change_allocation_source_name command is fired with {new_name}')
def step_impl(context, new_name):
    context.response = context.client.post('/api/v2/allocation_source_command',
                                           {"action": "change_allocation_source_name",
                                            "source_id": context.source_id,
                                            "name": new_name})
    context.new_name = new_name

@then('name is changed = {name_is_changed}')
def step_impl(context, name_is_changed):
    result = True if context.response.status_code == 201 else False
    if not result:
        assert result == _str2bool(name_is_changed.lower())
    else:
        assert result == _str2bool(name_is_changed.lower()) and context.response.data['name']==context.new_name

# Change Compute Allowed

@given('Allocation Source with compute_allowed')
def step_impl(context):
    for row in context.table:
        allocation_source = context.client.post('/api/v2/allocation_source_command',
                                                {"action": "create_allocation_source",
                                                 "renewal_strategy": 'default',
                                                 "name": "TestAllocationSource",
                                                 "compute_allowed": int(row["compute_allowed"])})

        context.old_compute_allowed = int(row['compute_allowed'])
        context.source_id = allocation_source.data['source_id']

@when('change_compute_allowed command is fired with {new_compute_allowed}')
def step_impl(context, new_compute_allowed):
    new_compute_allowed_delta = int(new_compute_allowed) - int(context.old_compute_allowed)
    context.response = context.client.post('/api/v2/allocation_source_command',
                                           {"action": "change_compute_allowed",
                                            "source_id": context.source_id,
                                            "compute_allowed": new_compute_allowed_delta})

    context.new_compute_allowed = int(new_compute_allowed)

@then('compute allowed is changed = {compute_allowed_is_changed}')
def step_impl(context, compute_allowed_is_changed):
    result = True if context.response.status_code == 201 else False
    if not result:
        assert result == _str2bool(compute_allowed_is_changed.lower())
    else:
        assert result == _str2bool(compute_allowed_is_changed.lower()) and context.response.data['compute_allowed'] == context.new_compute_allowed

# helper methods

def _str2bool(val):
    return True if val=='true' else False