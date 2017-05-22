import uuid
from datetime import timedelta

from behave import *
from business_rules import run_all
from dateutil.parser import parse
from dateutil.rrule import rrule, HOURLY
from django.test import modify_settings
from django.test.client import Client
from django.utils import timezone
from cyverse_allocation.tasks import update_snapshot_cyverse

from api.tests.factories import (
    InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ProviderMachineFactory, IdentityFactory, ProviderFactory, UserFactory)
from core.models import (
    AllocationSourceSnapshot, AllocationSource, Instance, Size,
    ProviderMachine, InstanceStatusHistory, AtmosphereUser)
from core.models.allocation_source import total_usage
from cyverse_allocation.cyverse_rules_engine_setup import CyverseTestRenewalVariables, CyverseTestRenewalActions, \
    cyverse_rules


######## Story Implementation ##########

@given('one admin user and two regular users who can launch instances')
def step_impl(context):
    context.client = Client()
    user = UserFactory.create(username='lenards', is_staff=True, is_superuser=True)
    user.set_password('lenards')
    user.save()
    with modify_settings(AUTHENTICATION_BACKENDS={
        'prepend': 'django.contrib.auth.backends.ModelBackend',
        'remove': ['django_cyverse_auth.authBackends.MockLoginBackend']
    }):
        context.admin_user = user
        context.client.login(username='lenards', password='lenards')

    user_1 = UserFactory.create(username='amitj')
    context.user_1 = user_1
    user_2 = UserFactory.create(username='julianp')
    context.user_2 = user_2


@when('admin creates allocation source')
def step_impl(context):
    context.allocation_sources = {}
    context.allocation_sources_name = {}
    context.current_time = timezone.now()
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                       {"renewal_strategy": row['renewal strategy'],
                                        "name": row['name'],
                                        "compute_allowed": row['compute allowed']})
        assert response.status_code == 201

        # if date_created is not current, change date_created to the custom date
        if str(row['date_created']) != 'current':
            date_created = parse(str(row['date_created']))
            allocation_source = AllocationSource.objects.filter(uuid=response.data['uuid']).last()
            allocation_source.start_date = date_created
            allocation_source.save()
        else:
            # this is to absolutely sync everything.. a difference of milliseconds can also result in incorrect values
            allocation_source = AllocationSource.objects.filter(uuid=response.data['uuid']).last()
            allocation_source.start_date = context.current_time
            allocation_source.save()

            source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=allocation_source).last()
            source_snapshot.updated = context.current_time
            source_snapshot.save()

        context.allocation_sources[row['allocation_source_id']] = response.data['uuid']
        context.allocation_sources_name[row['allocation_source_id']] = row['name']


@when('Users are added to allocation source')
def step_impl(context):
    for row in context.table:
        source_id = context.allocation_sources[row['allocation_source_id']]
        name = context.allocation_sources_name[row['allocation_source_id']]
        response = context.client.post('/api/v2/user_allocation_sources',
                                       {"username": row['username'],
                                        "allocation_source_name": name})

        assert response.status_code == 201


@when('User launch Instance')
def step_impl(context):
    context.instance = {}
    for row in context.table:
        user = AtmosphereUser.objects.get(username=row['username'])
        try:
            time_created = context.current_time if str(row['start_date']) == 'current' else parse(
                str(row['start_date']))
        except Exception as e:
            raise Exception('Parsing the start date caused an error %s' % (e))
        provider_alias = launch_instance(user, time_created, int(row["cpu"]))
        assert provider_alias is not None
        context.instance[row['instance_id']] = provider_alias


@when('User adds instance to allocation source')
def step_impl(context):
    for row in context.table:
        provider_alias = context.instance[row['instance_id']]
        context.client.get('/api/v2/emulate_session/%s' % (row['username']))
        source_id = context.allocation_sources[row['allocation_source_id']]
        name = context.allocation_sources_name[row['allocation_source_id']]
        response = context.client.post('/api/v2/instance_allocation_source',
                                       {"instance_id": provider_alias,
                                        "allocation_source_name": name})
        assert response.status_code == 201
    context.client.get('/api/v2/emulate_session/lenards')


@when('User instance runs for some days')
def step_impl(context):
    for row in context.table:
        user = AtmosphereUser.objects.filter(username=row['username']).last()
        provider_alias = context.instance[row['instance_id']]
        # get last instance_status_history
        last_history = InstanceStatusHistory.objects.filter(instance__provider_alias=provider_alias).order_by(
            'start_date').last()
        if str(row['status']) == 'active':
            time_stopped = last_history.start_date + timedelta(days=int(row['days']))
            change_instance_status(user, provider_alias, time_stopped, 'suspended')
        else:
            change_instance_status(user, provider_alias, last_history.start_date, row['status'])
            last_history.delete()


@then('calculate allocations used by allocation source after certain number of days')
def step_impl(context):
    current_time = context.current_time
    for row in context.table:
        allocation_source = AllocationSource.objects.filter(
            uuid=context.allocation_sources[row['allocation_source_id']]).last()
        start_date = current_time if str(row['report start date']) == 'current' else parse(
            str(row['report start date']))
        end_date = start_date + timedelta(days=int(row['number of days']))
        celery_iterator = list(rrule(HOURLY, interval=12, dtstart=start_date, until=end_date))

        prev_time = ''

        for current_time in celery_iterator:
            # update AllocationSourceSnapshot with the current compute_used
            if prev_time:
                update_snapshot_cyverse(end_date=current_time)
            prev_time=current_time

        compute_used_total = 0
        for user in allocation_source.all_users:
            compute_used_total += total_usage(user.username, start_date=start_date,
                                              end_date=end_date, allocation_source_name=allocation_source.name)

        compute_allowed = AllocationSourceSnapshot.objects.filter(
            allocation_source=allocation_source).last().compute_allowed
        compute_used_from_snapshot = AllocationSourceSnapshot.objects.filter(
            allocation_source=allocation_source).last().compute_used
        assert float(row['total compute used']) == compute_used_total
        assert float(row['current compute used']) == float(compute_used_from_snapshot)
        assert float(row['current compute allowed']) == float(compute_allowed)
        # assert (float(compute_allowed) - float(compute_used_from_snapshot)) == float(row['compute remaining'])


# @when('Users added to allocation source launch instance (at the same time)')
# def step_impl(context):
#     user = [context.user_1,context.user_2]
#     count = 0
#     time_created = timezone.now()
#     context.time_user_launched_instance = time_created
#     for row in context.table:
#         # add user to allocation source
#         context.client.post('/api/v2/user_allocation_sources',
#                             {"username": user[count].username,
#                              "source_id": context.uuid})
#         provider_alias = launch_instance(user[count],time_created,int(row["cpu"]))
#         # Add instance to allocation source
#         context.client.post('/api/v2/instance_allocation_source',
#                             {"instance_id": provider_alias,
#                              "source_id": context.uuid
#                              })
#         time_stopped = time_created + timedelta(days=int(row["days_instance_is_active"]))
#         stop_instance(user,provider_alias,time_stopped)
#         count+=1
#
#
# @then('after days = {no_of_days} Allocation source used = {compute_used} and remaining compute = {compute_remaining}')
# def step_impl(context, no_of_days, compute_used, compute_remaining):
#     #find how often renewal is fired for this strategy
#     current_time = timezone.now()
#     allocation_source = AllocationSource.objects.filter(uuid=context.uuid).last()
#     start_date = current_time
#     end_date = current_time+timedelta(days=int(no_of_days))
#     celery_iterator = list(rrule(HOURLY, interval=12, dtstart=start_date, until=end_date))
#
#     prev_time = ''
#
#     for current_time in celery_iterator:
#         # update AllocationSourceSnapshot with the current compute_used
#         if not prev_time:
#             prev_time = current_time
#         else:
#             snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=allocation_source).last()
#             snapshot.compute_used = float(snapshot.compute_used) + get_compute_used(allocation_source,current_time,prev_time)
#             snapshot.save()
#
#             run_all(rule_list=cyverse_rules,
#                     defined_variables=CyverseTestRenewalVariables(allocation_source, current_time),
#                     defined_actions=CyverseTestRenewalActions(allocation_source, current_time),
#                     )
#             prev_time=current_time
#
#     #find compute_used
#     compute_used_total = 0
#     for user in allocation_source.all_users:
#         compute_used_total += total_usage(user.username,start_date=context.time_user_launched_instance,end_date=end_date,allocation_source_name=allocation_source.name)
#     #find compute_remaining
#     compute_allowed = AllocationSourceSnapshot.objects.filter(allocation_source=allocation_source).last().compute_allowed
#     compute_used_from_snapshot = AllocationSourceSnapshot.objects.filter(
#         allocation_source=allocation_source).last().compute_used
#     assert int(compute_used) == compute_used_total
#     assert (float(compute_allowed)-float(compute_used_from_snapshot))==float(compute_remaining)

########### Helpers ###############

def launch_instance(user, time_created, cpu):
    # context.user is admin and regular user
    provider = ProviderFactory.create()
    from core.models import IdentityMembership, Identity
    user_group = IdentityMembership.objects.filter(member__name=user.username)
    if not user_group:
        user_identity = IdentityFactory.create_identity(
            created_by=user,
            provider=provider)
    else:
        user_identity = Identity.objects.all().last()
    admin_identity = user_identity

    provider_machine = ProviderMachine.objects.all()
    if not provider_machine:
        machine = ProviderMachineFactory.create_provider_machine(user, user_identity)
    else:
        machine = ProviderMachine.objects.all().last()

    status = InstanceStatusFactory.create(name='active')

    instance_state = InstanceFactory.create(
        provider_alias=uuid.uuid4(),
        source=machine.instance_source,
        created_by=user,
        created_by_identity=user_identity,
        start_date=time_created)

    size = Size(alias=uuid.uuid4(), name='small', provider=provider, cpu=cpu, disk=1, root=1, mem=1)
    size.save()
    InstanceHistoryFactory.create(
        status=status,
        activity="",
        instance=instance_state,
        start_date=time_created,
        size=size
    )

    return instance_state.provider_alias


def change_instance_status(user, provider_alias, time_stopped, new_status):
    active_instance = Instance.objects.filter(provider_alias=provider_alias).last()

    size = Size.objects.all().last()

    status_history = InstanceStatusHistory.objects.filter(instance=active_instance).last()
    status_history.end_date = time_stopped
    status_history.save()

    status = get_instance_state_from_factory(new_status)
    InstanceHistoryFactory.create(
        status=status,
        activity="",
        instance=active_instance,
        start_date=time_stopped,
        size=size
    )


def get_compute_used(allocation_source, current_time, prev_time):
    compute_used = 0
    for user in allocation_source.all_users:
        compute_used += total_usage(user.username, start_date=prev_time,
                                    end_date=current_time, allocation_source_name=allocation_source.name)

    return compute_used


def get_instance_state_from_factory(status):
    if str(status) == 'active':
        return InstanceStatusFactory.create(name='active')
    if str(status) == 'deploy_error':
        return InstanceStatusFactory.create(name='deploy_error')
    if str(status) == 'networking':
        return InstanceStatusFactory.create(name='networking')
    if str(status) == 'suspended':
        return InstanceStatusFactory.create(name='suspended')
