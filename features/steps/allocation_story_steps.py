import uuid
from datetime import timedelta

# noinspection PyUnresolvedReferences
from behave import *    # noqa
from behave import when, then, given
from dateutil.parser import parse
from dateutil.rrule import rrule, HOURLY
from django.test import modify_settings
from django.test.client import Client
from django.utils import timezone

from api.tests.factories import (
    InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ProviderMachineFactory, IdentityFactory, ProviderFactory, UserFactory
)
from core.models import (
    AllocationSourceSnapshot, AllocationSource, Instance, Size, ProviderMachine,
    InstanceStatusHistory, AtmosphereUser, EventTable,
    InstanceAllocationSourceSnapshot
)
from core.models.allocation_source import total_usage
from cyverse_allocation.tasks import update_snapshot_cyverse, renew_allocation_sources

######## Story Implementation ##########


@given('one admin user and two regular users who can launch instances')
def create_admin_and_two_regular_users(context):
    context.client = Client()
    user = UserFactory.create(
        username='lenards', is_staff=True, is_superuser=True
    )
    user.set_password('lenards')
    user.save()
    with modify_settings(
        AUTHENTICATION_BACKENDS={
            'prepend': 'django.contrib.auth.backends.ModelBackend',
            'remove': ['django_cyverse_auth.authBackends.MockLoginBackend']
        }
    ):
        context.admin_user = user
        context.client.login(username='lenards', password='lenards')

    user_1 = UserFactory.create(username='amitj')
    context.user_1 = user_1
    user_2 = UserFactory.create(username='julianp')
    context.user_2 = user_2


@when('admin creates allocation source')
def admin_create_allocation_source(context):
    context.allocation_sources = {}
    context.allocation_sources_name = {}
    context.current_time = timezone.now()
    for row in context.table:
        response = context.client.post(
            '/api/v2/allocation_sources', {
                "renewal_strategy": row['renewal strategy'],
                "name": row['name'],
                "compute_allowed": row['compute allowed']
            }
        )
        assert response.status_code == 201

        # if date_created is not current, change date_created to the custom date
        if str(row['date_created']) != 'current':
            date_created = parse(str(row['date_created']))
            allocation_source = AllocationSource.objects.filter(
                uuid=response.data['uuid']
            ).last()
            allocation_source.start_date = date_created
            allocation_source.save()
        else:
            # this is to absolutely sync everything.. a difference of milliseconds can also result in incorrect values
            allocation_source = AllocationSource.objects.filter(
                uuid=response.data['uuid']
            ).last()
            allocation_source.start_date = context.current_time
            allocation_source.save()

            source_snapshot = AllocationSourceSnapshot.objects.filter(
                allocation_source=allocation_source
            ).last()
            source_snapshot.updated = context.current_time
            source_snapshot.save()

        context.allocation_sources[row['allocation_source_id']
                                  ] = response.data['uuid']
        context.allocation_sources_name[row['allocation_source_id']
                                       ] = row['name']


@when('Users are added to allocation source')
def add_users_to_allocation(context):
    for row in context.table:
        name = context.allocation_sources_name[row['allocation_source_id']]
        response = context.client.post(
            '/api/v2/user_allocation_sources', {
                "username": row['username'],
                "allocation_source_name": name
            }
        )

        assert response.status_code == 201


@when('User launch Instance')
def launch_instance_for_user(context):
    if not hasattr(context, 'instance'):
        context.instance = {}
    for row in context.table:
        user = AtmosphereUser.objects.get(username=row['username'])
        try:
            time_created = context.current_time if str(
                row['start_date']
            ) == 'current' else parse(str(row['start_date']))
        except Exception as e:
            raise Exception('Parsing the start date caused an error %s' % (e))
        provider_alias = launch_instance(user, time_created, int(row["cpu"]))
        assert provider_alias is not None
        context.instance[row['instance_id']] = provider_alias


@when('User adds instance to allocation source')
def add_allocation_instance(context):
    for row in context.table:
        provider_alias = context.instance[row['instance_id']]
        emulate_response = context.client.get(
            '/api/v2/emulate_session/%s' % (row['username'])
        )
        context.test.assertEqual(emulate_response.status_code, 201)
        name = context.allocation_sources_name[row['allocation_source_id']]
        response = context.client.post(
            '/api/v2/instance_allocation_source', {
                "instance_id": provider_alias,
                "allocation_source_name": name
            }
        )
        context.test.assertEqual(response.status_code, 201)
    unemulate_response = context.client.get('/api/v2/emulate_session/lenards')
    context.test.assertEqual(unemulate_response.status_code, 201)


@when('User instance runs for some days')
def instance_runs_for_some_days(context):
    for row in context.table:
        user = AtmosphereUser.objects.filter(username=row['username']).last()
        provider_alias = context.instance[row['instance_id']]
        # get last instance_status_history
        last_history = InstanceStatusHistory.objects.filter(
            instance__provider_alias=provider_alias
        ).order_by('start_date').last()
        if str(row['status']) == 'active':
            time_stopped = last_history.start_date + timedelta(
                days=int(row['days'])
            )
            change_instance_status(
                user, provider_alias, time_stopped, 'suspended'
            )
        else:
            change_instance_status(
                user, provider_alias, last_history.start_date, row['status']
            )
            last_history.delete()


@then(
    'calculate allocations used by allocation source after certain number of days'
)
def calculate_allocations_used_by_allocation_source_after_certain_number_of_days(
    context
):
    current_time = context.current_time
    for row in context.table:
        allocation_source = AllocationSource.objects.filter(
            name=context.allocation_sources_name[row['allocation_source_id']]
        ).last()

        start_date = current_time if str(
            row['report start date']
        ) == 'current' else parse(str(row['report start date']))
        end_date = start_date + timedelta(days=int(row['number of days']))
        celery_iterator = list(
            rrule(HOURLY, interval=12, dtstart=start_date, until=end_date)
        )

        prev_time = ''

        for current_time in celery_iterator:
            # update AllocationSourceSnapshot with the current compute_used
            if prev_time:
                update_snapshot_cyverse(end_date=current_time)
            prev_time = current_time

        context.time_at_the_end_of_calculation_check = current_time

        compute_used_total = 0
        for user in allocation_source.all_users:
            compute_used_total += total_usage(
                user.username,
                start_date=start_date,
                end_date=end_date,
                allocation_source_name=context.allocation_sources_name[
                    row['allocation_source_id']]
            )

        compute_allowed = AllocationSourceSnapshot.objects.filter(
            allocation_source=allocation_source
        ).last().compute_allowed
        compute_used_from_snapshot = AllocationSourceSnapshot.objects.filter(
            allocation_source=allocation_source
        ).last().compute_used
        assert float(row['total compute used']
                    ) == float(compute_used_from_snapshot)
        assert float(row['current compute used']
                    ) == float(compute_used_from_snapshot)
        assert float(row['current compute allowed']) == float(compute_allowed)
        # assert (float(compute_allowed) - float(compute_used_from_snapshot)) == float(row['compute remaining'])


# Alternate Story Step Implementation


@when('User launch Instance and no statushistory is created')
def user_launch_Instance_and_no_statushistory_is_created(context):
    context.instance = {}
    context.instance_history_args = {}
    for row in context.table:
        user = AtmosphereUser.objects.get(username=row['username'])
        try:
            time_created = context.current_time if str(
                row['start_date']
            ) == 'current' else parse(str(row['start_date']))
        except Exception as e:
            raise Exception('Parsing the start date caused an error %s' % (e))
        instance, status = launch_instance(
            user, time_created, int(row["cpu"]), before=True
        )
        provider_alias = instance.provider_alias
        assert provider_alias is not None
        context.instance[row['instance_id']] = provider_alias
        context.instance_history_args[row['instance_id']] = {
            'instance': instance,
            'provider': instance.provider,
            'status': status,
            'cpu': int(row["cpu"])
        }


@when(
    'Instance Allocation Source Changed Event is fired BEFORE statushistory is created'
)
def instance_allocation_source_changed_event_is_fired_before_statushistory_is_created(
    context
):
    for row in context.table:
        payload = {}
        payload['allocation_source_name'] = context.allocation_sources_name[
            row["allocation_source_id"]]
        payload['instance_id'] = str(context.instance[row['instance_id']])

        name = 'instance_allocation_source_changed'
        ts = context.current_time
        entity_id = str(row["username"])

        event = EventTable(
            name=name, payload=payload, timestamp=ts, entity_id=entity_id
        )
        event.save()

        # test the obj was created
        obj = InstanceAllocationSourceSnapshot.objects.filter(
            allocation_source__name=payload['allocation_source_name'],
            instance__provider_alias=payload['instance_id']
        )

        assert (len(obj) == 1)

        # create status history
        args = context.instance_history_args[row['instance_id']]
        time_created = ts + timedelta(seconds=3)
        launch_instance_history(
            args['instance'], args['cpu'], args['provider'], args['status'],
            time_created
        )


# Tests for one off renewal event


@then('Compute Allowed is increased for Allocation Source')
def compute_allowed_is_increased_for_allocation_source(context):
    for row in context.table:
        allocation_source_name = context.allocation_sources_name[
            row['allocation_source_id']]
        new_compute_allowed = int(row['new_compute_allowed'])

        payload = {}
        payload['allocation_source_name'] = allocation_source_name
        payload['compute_allowed'] = new_compute_allowed
        name = 'allocation_source_compute_allowed_changed'
        ts = context.time_at_the_end_of_calculation_check

        event = EventTable(
            name=name,
            entity_id=allocation_source_name,
            payload=payload,
            timestamp=ts
        )
        event.save()

        assert AllocationSource.objects.get(
            name=allocation_source_name
        ).compute_allowed == new_compute_allowed


@then('One off Renewal task is run without rules engine')
def one_off_renewal_task_is_run_without_rules_engine(context):
    time = context.time_at_the_end_of_calculation_check
    renew_allocation_sources(current_time=time)

    for row in context.table:
        allocation_source = AllocationSource.objects.filter(
            name=context.allocation_sources_name[row['allocation_source_id']]
        ).last()

        renewal_event = EventTable.objects.filter(
            name='allocation_source_created_or_renewed',
            payload__allocation_source_name=allocation_source.name,
            timestamp=time
        )
        assert len(renewal_event) > 0
        assert float(allocation_source.snapshot.compute_used) == float(
            row['current compute used']
        )
        assert float(allocation_source.snapshot.compute_allowed) == float(
            row['current compute allowed']
        )


def launch_instance(user, time_created, cpu, before=False):
    # context.user is admin and regular user
    provider = ProviderFactory.create()
    from core.models import IdentityMembership, Identity
    user_group = IdentityMembership.objects.filter(member__name=user.username)
    if not user_group:
        user_identity = IdentityFactory.create_identity(
            created_by=user, provider=provider
        )
    else:
        user_identity = Identity.objects.all().last()
    provider_machine = ProviderMachine.objects.all()
    if not provider_machine:
        machine = ProviderMachineFactory.create_provider_machine(
            user, user_identity
        )
    else:
        machine = ProviderMachine.objects.all().last()

    status = InstanceStatusFactory.create(name='active')

    instance_state = InstanceFactory.create(
        provider_alias=uuid.uuid4(),
        source=machine.instance_source,
        created_by=user,
        created_by_identity=user_identity,
        start_date=time_created
    )

    if not before:
        return launch_instance_history(
            instance_state, cpu, provider, status, time_created
        )

    return instance_state, status


def launch_instance_history(
    instance_state, cpu, provider, status, time_created
):
    size = Size(
        alias=uuid.uuid4(),
        name='small',
        provider=provider,
        cpu=cpu,
        disk=1,
        root=1,
        mem=1
    )
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
    active_instance = Instance.objects.filter(provider_alias=provider_alias
                                             ).last()

    size = Size.objects.all().last()

    status_history = InstanceStatusHistory.objects.filter(
        instance=active_instance
    ).last()
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
        compute_used += total_usage(
            user.username,
            start_date=prev_time,
            end_date=current_time,
            allocation_source_name=allocation_source.name
        )

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
