import json
import uuid

from behave import *
from decimal import Decimal
from django.core.urlresolvers import reverse
from django.test import modify_settings
from django.test.client import Client
from django.utils import timezone
from rest_framework.test import APIClient

from api.tests.factories import (
    InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ProviderMachineFactory, IdentityFactory, ProviderFactory, UserFactory)
from core.models import AllocationSourceSnapshot, Instance
from core.models.allocation_source import get_allocation_source_object


@given('an admin user "{username}"')
def create_admin_user(context, username):
    context.client = Client()
    user = UserFactory.create(username=username, is_staff=True, is_superuser=True)
    user.set_password(username)
    user.save()
    with modify_settings(AUTHENTICATION_BACKENDS={
        'prepend': 'django.contrib.auth.backends.ModelBackend',
        'remove': ['django_cyverse_auth.authBackends.MockLoginBackend']
    }):
        context.user = user
        context.client.login(username=username, password=username)


@given('a user "{username}"')
def create_user_with_username(context, username):
    context.client = Client()
    user = UserFactory.create(username=username, is_staff=False, is_superuser=False)
    user.set_password(username)
    user.save()
    with modify_settings(AUTHENTICATION_BACKENDS={
        'prepend': 'django.contrib.auth.backends.ModelBackend',
        'remove': ['django_cyverse_auth.authBackends.MockLoginBackend']
    }):
        context.user = user
        context.client.login(username=username, password=username)


# Allocation Source Creation


@when('create_allocation_source command is fired')
def step_impl(context):
    for row in context.table:
        context.response = context.client.post('/api/v2/allocation_sources',
                                               {"renewal_strategy": row['renewal strategy'],
                                                "name": row['name'],
                                                "compute_allowed": row['compute allowed']})


@then('allocation source is created = {allocation_source_is_created}')
def step_impl(context, allocation_source_is_created):
    result = True if context.response.status_code == 201 else False
    assert result == _str2bool(allocation_source_is_created.lower())


# Change Renewal Event

@given('An Allocation Source with renewal strategy')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                       {"renewal_strategy": row['renewal strategy'],
                                        "name": "TestAllocationSource",
                                        "compute_allowed": 5000})
        context.source_id = response.data['uuid']


@when('change_renewal_strategy command is fired with {new_renewal_strategy}')
def step_impl(context, new_renewal_strategy):
    # Django Client PATCH method requires json dumped data and Content-Type
    # otherwise it returns 415
    context.response = context.client.patch('/api/v2/allocation_sources/%s' % (context.source_id),
                                            json.dumps({"renewal_strategy": new_renewal_strategy}),
                                            content_type='application/json')
    context.new_renewal_strategy = new_renewal_strategy


@then('renewal strategy is changed = {renewal_strategy_is_changed}')
def step_impl(context, renewal_strategy_is_changed):
    result = True if context.response.status_code == 200 else False
    if not result:
        assert result == _str2bool(renewal_strategy_is_changed.lower())
    else:
        assert result == _str2bool(renewal_strategy_is_changed.lower()) and context.response.data[
                                                                                'renewal_strategy'] == context.new_renewal_strategy


# Change Allocation Source Name

@given('An Allocation Source with name')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                       {"renewal_strategy": 'default',
                                        "name": row['name'],
                                        "compute_allowed": 5000})

        context.source_id = response.data['uuid']


@when('change_allocation_source_name command is fired with {new_name}')
def step_impl(context, new_name):
    context.response = context.client.patch('/api/v2/allocation_sources/%s' % (context.source_id),
                                            json.dumps({"name": new_name}), content_type='application/json')
    context.new_name = new_name


@then('name is changed = {name_is_changed}')
def step_impl(context, name_is_changed):
    result = True if context.response.status_code == 200 else False
    if not result:
        assert result == _str2bool(name_is_changed.lower())
    else:
        assert result == _str2bool(name_is_changed.lower()) and context.response.data[
                                                                    'name'] == context.new_name


# Change Compute Allowed


@given('Allocation Source with compute allowed and compute used')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                       {"renewal_strategy": 'default',
                                        "name": "TestAllocationSource",
                                        "compute_allowed": int(row["compute_allowed"])})

        context.old_compute_allowed = row['compute_allowed']
        context.source_id = response.data['uuid']

        # set compute used for AllocationSourceSnapshot if compute_used > 0
        if int(row['compute_used']) > 0 and response.status_code == 201:
            allocation_source = get_allocation_source_object(context.source_id)
            snapshot = AllocationSourceSnapshot.objects.get(
                allocation_source=allocation_source)
            snapshot.compute_used = int(row['compute_used'])
            snapshot.save()


@when('change_compute_allowed command is fired with {new_compute_allowed}')
def step_impl(context, new_compute_allowed):
    context.response = context.client.patch('/api/v2/allocation_sources/%s' % (context.source_id),
                                            json.dumps({"compute_allowed": int(new_compute_allowed)}),
                                            content_type='application/json')

    context.new_compute_allowed = int(new_compute_allowed)


@then('compute allowed is changed = {compute_allowed_is_changed}')
def step_impl(context, compute_allowed_is_changed):
    result = True if context.response.status_code == 200 else False
    if not result:
        assert result == _str2bool(compute_allowed_is_changed.lower())
    else:
        assert result == _str2bool(compute_allowed_is_changed.lower()) and context.response.data[
                                                                               'compute_allowed'] == context.new_compute_allowed


@given('Allocation Source')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                       {"renewal_strategy": row['renewal strategy'],
                                        "name": row['name'],
                                        "compute_allowed": row['compute allowed']})
        context.source_id = response.data['uuid']
        context.name = row['name']


@when('User is assigned to the allocation source')
def step_impl(context):
    context.response = context.client.post('/api/v2/user_allocation_sources',
                                           {"username": context.user.username,
                                            "allocation_source_name": context.name})


@then('User assignment = {user_is_assigned}')
def step_impl(context, user_is_assigned):
    result = True if context.response.status_code == 201 else False
    assert result == _str2bool(user_is_assigned.lower())


@given('User assigned to Allocation Source')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                       {"renewal_strategy": row['renewal strategy'],
                                        "name": row['name'],
                                        "compute_allowed": row['compute allowed']})

        context.source_id = response.data['uuid']
        context.name = row['name']

        response_main = context.client.post('/api/v2/user_allocation_sources',
                                            {"username": context.user.username,
                                             "allocation_source_name": context.name})


@when('User is removed from Allocation Source')
def step_impl(context):
    context.response = context.client.delete('/api/v2/user_allocation_sources',
                                             json.dumps({"username": context.user.username,
                                                         "allocation_source_name": context.name}),
                                             content_type='application/json')


@then('User removal = {user_is_removed}')
def step_impl(context, user_is_removed):
    result = True if context.response.status_code == 200 else False
    assert result == _str2bool(user_is_removed.lower())


# helper methods


@when('Allocation Source is removed')
def step_impl(context):
    context.response = context.client.delete('/api/v2/allocation_sources/%s' % (context.source_id),
                                             content_type='application/json')


@then('Allocation Source Removal = {allocation_source_is_removed}')
def step_impl(context, allocation_source_is_removed):
    result = True if context.response.status_code == 200 else False
    allocation_source = get_allocation_source_object(context.source_id)
    allocation_source_end_date = allocation_source.end_date
    assert result == _str2bool(allocation_source_is_removed.lower()) and \
           allocation_source_end_date is not None


@given("Pre-initalizations")
def step_impl(context):
    # context.user is admin and regular user
    provider = ProviderFactory.create()
    from core.models import IdentityMembership, Identity, ProviderMachine
    user_group = IdentityMembership.objects.all()
    if not user_group:
        user_identity = IdentityFactory.create_identity(
            created_by=context.user,
            provider=provider)
    else:
        user_identity = Identity.objects.all().last()
    admin_identity = user_identity

    provider_machine = ProviderMachine.objects.all()
    if not provider_machine:
        machine = ProviderMachineFactory.create_provider_machine(
            context.user, user_identity)
    else:
        machine = ProviderMachine.objects.all().last()
    context.active_instance = InstanceFactory.create(
        name="Instance in active",
        provider_alias=uuid.uuid4(),
        source=machine.instance_source,
        created_by=context.user,
        created_by_identity=user_identity,
        start_date=timezone.now())

    active = InstanceStatusFactory.create(name='active')
    InstanceHistoryFactory.create(
        status=active,
        activity="",
        instance=context.active_instance
    )


@when("User launches instance")
def step_impl(context):
    client = APIClient()
    client.force_authenticate(user=context.user)

    url = reverse('api:v2:instance-detail',
                  args=(context.active_instance.provider_alias,))
    context.response = client.get(url)
    context.provider_alias = context.response.data["version"]["id"]


@then("Instance is launched")
def step_impl(context):
    assert context.response.status_code == 200
    data = context.response.data
    assert data['status'] == 'active'
    assert data['activity'] == ''


@given('User assigned to Allocation Source and User with an Instance')
def step_impl(context):
    for row in context.table:
        context.execute_steps(u"""
                    given Pre-initalizations
                    when User launches instance
                """)
        response = context.client.post('/api/v2/allocation_sources',
                                       {"renewal_strategy": row['renewal strategy'],
                                        "name": row['name'],
                                        "compute_allowed": row['compute allowed']})

        context.source_id = response.data['uuid']
        context.name = row['name']
        response_main = context.client.post('/api/v2/user_allocation_sources',
                                            {"username": context.user.username,
                                             "allocation_source_name": context.name})


@when('User assigns allocation source to instance')
def step_impl(context):
    context.response = context.client.post('/api/v2/instance_allocation_source',
                                           {"instance_id": Instance.objects.all().last().provider_alias,
                                            "allocation_source_name": context.name
                                            })


@then('Instance is assigned = {instance_is_assigned}')
def step_impl(context, instance_is_assigned):
    result = True if context.response.status_code == 201 else False
    assert result == _str2bool(instance_is_assigned.lower())


def _str2bool(val):
    return True if val == 'true' else False


@when('the user allocation snapshot for "{username}" and "{allocation_source_name}" is deleted')
def delete_user_allocation_snapshot(context, username, allocation_source_name):
    import core.models
    user = core.models.AtmosphereUser.objects.get_by_natural_key(username)
    context.test.assertIsInstance(user, core.models.AtmosphereUser)
    allocation_source = core.models.AllocationSource.objects.get(name=allocation_source_name)
    context.test.assertIsInstance(allocation_source, core.models.AllocationSource)
    user_allocation_snapshot = core.models.UserAllocationSnapshot.objects.get(
        user=user,
        allocation_source=allocation_source)
    context.test.assertIsInstance(user_allocation_snapshot, core.models.UserAllocationSnapshot)
    delete_result = user_allocation_snapshot.delete()
    context.test.assertTrue(delete_result)


@step('time remaining on allocation source "{allocation_source_name}" is {time_remaining:f}')
def time_remaining_on_allocation_source(context, allocation_source_name, time_remaining):
    import core.models
    allocation_source = core.models.AllocationSource.objects.get(name=allocation_source_name)
    context.test.assertIsInstance(allocation_source, core.models.AllocationSource)
    actual_remaining_compute = allocation_source.time_remaining()
    context.test.assertAlmostEqual(actual_remaining_compute, Decimal(time_remaining), delta=0.1)


@step('allocation source "{allocation_source_name}" is not over allocation')
def allocation_source_is_over_allocation(context, allocation_source_name):
    import core.models
    allocation_source = core.models.AllocationSource.objects.get(name=allocation_source_name)
    context.test.assertIsInstance(allocation_source, core.models.AllocationSource)
    is_over_allocation = allocation_source.is_over_allocation()
    context.test.assertFalse(is_over_allocation)
