from behave import *
from django.test.client import Client
from core.models import AtmosphereUser
from core.models import AllocationSourceSnapshot, AllocationSource
import json

@given('a user')
def step_impl(context):
    context.client = Client()
    # the only user who can access apis on dev is lenards, so set staff permission for lenards on test db
    user, not_created = AtmosphereUser.objects.get_or_create(username='lenards', password='lenards')
    if not_created:
        user.is_staff = True
        user.is_superuser = True
        user.save()
    context.user = user
    context.client.login()

# Allocation Source Creation

@when('create_allocation_source command is fired')
def step_impl(context):
    for row in context.table:
        context.response = context.client.post('/api/v2/allocation_sources',
                                               {"renewal_strategy": row['renewal strategy'],
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
        response = context.client.post('/api/v2/allocation_sources',
                                               {"renewal_strategy": row['renewal strategy'],
                                                "name": "TestAllocationSource",
                                                "compute_allowed": 5000})
        context.source_id = response.data['source_id']

@when('change_renewal_strategy command is fired with {new_renewal_strategy}')
def step_impl(context, new_renewal_strategy):

    # Django Client PATCH method requires json dumped data and Content-Type otherwise it returns 415

    context.response = context.client.patch('/api/v2/allocation_sources/%s'%(context.source_id),
                                           json.dumps({"renewal_strategy": new_renewal_strategy}),content_type='application/json')
    context.new_renewal_strategy = new_renewal_strategy

@then('renewal strategy is changed = {renewal_strategy_is_changed}')
def step_impl(context, renewal_strategy_is_changed):
    result = True if context.response.status_code == 200 else False
    if not result:
        assert result == _str2bool(renewal_strategy_is_changed.lower())
    else:
        assert result == _str2bool(renewal_strategy_is_changed.lower()) and context.response.data['renewal_strategy']==context.new_renewal_strategy


# Change Allocation Source Name

@given('An Allocation Source with name')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                                {"renewal_strategy": 'default',
                                                 "name": row['name'],
                                                 "compute_allowed": 5000})

        context.source_id = response.data['source_id']

@when('change_allocation_source_name command is fired with {new_name}')
def step_impl(context, new_name):
    context.response = context.client.patch('/api/v2/allocation_sources/%s'%(context.source_id),
                                                   json.dumps({"name": new_name}),content_type='application/json')
    context.new_name = new_name

@then('name is changed = {name_is_changed}')
def step_impl(context, name_is_changed):
    result = True if context.response.status_code == 200 else False
    if not result:
        assert result == _str2bool(name_is_changed.lower())
    else:
        assert result == _str2bool(name_is_changed.lower()) and context.response.data['name']==context.new_name

# Change Compute Allowed

@given('Allocation Source with compute allowed and compute used')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                                { "renewal_strategy": 'default',
                                                 "name": "TestAllocationSource",
                                                 "compute_allowed": int(row["compute_allowed"])})

        context.old_compute_allowed = row['compute_allowed']
        context.source_id = response.data['source_id']

        # set compute used for AllocationSourceSnapshot if compute_used > 0
        if int(row['compute_used'])>0 and response.status_code==201:
            snapshot = AllocationSourceSnapshot.objects.get(allocation_source__source_id=context.source_id)
            snapshot.compute_used = int(row['compute_used'])
            snapshot.save()

@when('change_compute_allowed command is fired with {new_compute_allowed}')
def step_impl(context, new_compute_allowed):
    context.response = context.client.patch('/api/v2/allocation_sources/%s'%(context.source_id),
                                           json.dumps({"compute_allowed": int(new_compute_allowed)}),content_type='application/json')

    context.new_compute_allowed = int(new_compute_allowed)

@then('compute allowed is changed = {compute_allowed_is_changed}')
def step_impl(context, compute_allowed_is_changed):
    result = True if context.response.status_code == 200 else False
    if not result:
        assert result == _str2bool(compute_allowed_is_changed.lower())
    else:
        assert result == _str2bool(compute_allowed_is_changed.lower()) and context.response.data['compute_allowed'] == context.new_compute_allowed


@given('Allocation Source')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                               {"renewal_strategy": row['renewal strategy'],
                                                "name": row['name'],
                                                "compute_allowed": row['compute allowed']})
        context.source_id = response.data['source_id']

@when('User is assigned to the allocation source')
def step_impl(context):
    context.response = context.client.post('/api/v2/user_allocation_sources',
                        {"username": context.user.username,
                         "source_id": context.source_id})

@then('User assignment = {user_is_assigned}')
def step_impl(context,user_is_assigned):
    result = True if context.response.status_code == 201 else False
    assert result == _str2bool(user_is_assigned.lower())

@given('User assigned to Allocation Source')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                                   {"renewal_strategy": row['renewal strategy'],
                                                    "name": row['name'],
                                                    "compute_allowed": row['compute allowed']})

        context.source_id = response.data['source_id']

        response_main = context.client.post('/api/v2/user_allocation_sources',
                        {"username": context.user.username,
                         "source_id": context.source_id})


@when('User is removed from Allocation Source')
def step_impl(context):
    context.response = context.client.delete('/api/v2/user_allocation_sources',
                                             json.dumps({"username":context.user.username,
                                                         "source_id":context.source_id}),
                                             content_type='application/json')

@then('User removal = {user_is_removed}')
def step_impl(context,user_is_removed):
    result = True if context.response.status_code == 200 else False
    assert result == _str2bool(user_is_removed.lower())
# helper methods

def _str2bool(val):
    return True if val=='true' else False


@when('Allocation Source is removed')
def step_impl(context):
    context.response = context.client.delete('/api/v2/allocation_sources/%s'%(context.source_id),
                                             content_type='application/json')

@then('Allocation Source Removal = {allocation_source_is_removed}')
def step_impl(context, allocation_source_is_removed):
    result = True if context.response.status_code == 200 else False
    allocation_source_end_date = AllocationSource.objects.filter(
        source_id=context.source_id).last().end_date
    assert result == _str2bool(allocation_source_is_removed.lower()) and \
           allocation_source_end_date is not None