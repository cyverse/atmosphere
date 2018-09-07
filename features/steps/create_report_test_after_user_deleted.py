import logging
import uuid
from datetime import timedelta

# noinspection PyUnresolvedReferences
from behave import * # noqa
from behave import when, then, given
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone

from api.tests.factories import (
    UserFactory, InstanceFactory, IdentityFactory, InstanceStatusFactory,
    ProviderFactory, ProviderMachineFactory, InstanceHistoryFactory)
from core.models.allocation_source import total_usage
from jetstream.exceptions import TASPluginException
from core.models import (
    AllocationSource, UserAllocationSource, EventTable,
    InstanceStatusHistory, ProviderMachine, Size,
    AtmosphereUser
)
from jetstream.models import TASAllocationReport
from jetstream.allocation import TASAPIDriver

logger = logging.getLogger(__name__)

@given('a test Allocation Source')
def a_test_allocation_source(context):
    context.current_time = timezone.now()
    name, compute_allowed = "testSource", 1000
    context.allocation_source = AllocationSource.objects.create(name=name, compute_allowed=compute_allowed)
    # source = AllocationSource.objects.filter(name=name)
    assert (len(AllocationSource.objects.filter(name=name)) > 0)


@when('Allocation Source is assigned to Users')
def allocation_source_is_assigned_to_users(context):
    context.users = []
    for row in context.table:
        number_of_users = int(row['number of users assigned to allocation source'])
        context.number_of_users = number_of_users

    for i in range(number_of_users):
        user = UserFactory.create(date_joined=context.current_time)
        context.users.append(user)
        UserAllocationSource.objects.create(allocation_source=context.allocation_source, user=user)
        assert (len(UserAllocationSource.objects.filter(user=user, allocation_source=context.allocation_source)) > 0)


@when('All Users run an instance on Allocation Source for indefinite duration')
def all_users_run_an_instance_on_allocation_source_for_indefinite_duration(context):
    for row in context.table:
        cpu_size = int(row['cpu size of instance'])
        context.cpu_size = cpu_size

    for user in context.users:
        alias = launch_instance(user, context.current_time, cpu_size)
        payload = {}
        payload["instance_id"] = str(alias)
        payload["allocation_source_name"] = context.allocation_source.name

        EventTable.objects.create(name="instance_allocation_source_changed",
                                  payload=payload,
                                  entity_id=user.username,
                                  timestamp=context.current_time)

        assert (len(InstanceStatusHistory.objects.filter(instance__created_by=user)) == 1)


@when('create_reports task is run for the first time')
def create_reports_task_is_run_for_the_first_time(context):
    for row in context.table:
        interval_time = int(row['task runs every x minutes'])
        context.interval_time = interval_time

    report_end_date = context.current_time + timedelta(minutes=interval_time)

    create_reports(end_date=report_end_date)

    assert (len(TASAllocationReport.objects.all()) > 0)
    assert (TASAllocationReport.objects.last().end_date == report_end_date)
    assert (TASAllocationReport.objects.last().start_date == context.current_time)

    expected_initial_usage = context.cpu_size * context.interval_time * context.number_of_users
    calculated_initial_usage = float(
        TASAllocationReport.objects.filter(project_name=context.allocation_source.name).aggregate(Sum('compute_used'))[
            'compute_used__sum']) * 60

    assert (round(calculated_initial_usage, 2) == expected_initial_usage)

    context.current_time = context.current_time + timedelta(minutes=interval_time)


@when('Users are deleted from Allocation Source after first create_reports run')
def users_are_deleted_from_allocation_source_after_first_create_reports_run(context):
    for row in context.table:
        users_deleted = int(row['number of users deleted from allocation source'])
        users_deleted_after_time = int(row['users deleted x minutes after the first create_reports run'])

    for i in range(users_deleted):
        user = context.users[i]
        payload = {}
        payload["allocation_source_name"] = context.allocation_source.name
        EventTable.objects.create(
            payload=payload,
            name="user_allocation_source_deleted",
            entity_id=user.username,
            timestamp=context.current_time + timedelta(minutes=users_deleted_after_time))

        assert (len(UserAllocationSource.objects.filter(user=user, allocation_source=context.allocation_source)) == 0)


@then('Total expected allocation usage for allocation source matches calculated allocation usage from reports after next create_reports run')
def total_expected_allocation_usage_for_allocation_source_matches_calculated_allocation_usage_from_reports_after_next_create_reports_run(context):
    for row in context.table:
        total_expected_usage = int(row['total expected allocation usage in minutes'])

    report_end_date = context.current_time + timedelta(minutes=context.interval_time)
    create_reports(end_date=report_end_date)

    assert (len(TASAllocationReport.objects.all()) == 2 * context.number_of_users)
    assert (TASAllocationReport.objects.last().start_date == context.current_time)

    calculated_initial_usage = float(
        TASAllocationReport.objects.filter(project_name=context.allocation_source.name).aggregate(Sum('compute_used'))[
            'compute_used__sum']) * 60

    logging.info("\n\n expected:%s  actual:%s \n\n" % (total_expected_usage, int(calculated_initial_usage)))

    # just for the purpose of these test cases, we require time in minutes
    # conversion from microseconds to hours and then hours to minutes with rounding results in loss of time
    # therefore instead of comparing exact values, we check if the difference is not more than a minute (or two)

    assert (abs(total_expected_usage - int(calculated_initial_usage)) < 2)


#### Helpers ####

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
        end_date=time_created + timedelta(minutes=30),
        size=size
    )

    return instance_state.provider_alias


def create_reports(end_date=False):
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    user_allocation_list = UserAllocationSource.objects.all()
    all_reports = []

    if not end_date:
        end_date = timezone.now()
    last_report_date = TASAllocationReport.objects.order_by('end_date')

    if not last_report_date:
        last_report_date = end_date
    else:
        last_report_date = last_report_date.last().end_date

    for item in user_allocation_list:
        allocation_name = item.allocation_source.name
        # CHANGED LINE
        project_report = _create_reports_for(item.user, allocation_name, end_date)
        if project_report:
            all_reports.append(project_report)

    # Take care of Deleted Users

    # filter user_allocation_source_removed events which are created after the last report date

    for event in EventTable.objects.filter(name="user_allocation_source_deleted", timestamp__gte=last_report_date).order_by('timestamp'):

        user = AtmosphereUser.objects.get(username=event.entity_id)
        allocation_name = event.payload['allocation_source_name']
        end_date = event.timestamp
        project_report = _create_reports_for(user, allocation_name, end_date)
        if project_report:
            all_reports.append(project_report)
    return all_reports


def _create_reports_for(user, allocation_name, end_date):
    tacc_username = user.username
    if not tacc_username:
        logger.error("No TACC username for user: '{}' which came from allocation id: {}".format(user,
                                                                                                allocation_name))
        return
    project_name = allocation_name
    try:
        project_report = _create_tas_report_for(
            user,
            tacc_username,
            project_name,
            end_date)
        return project_report
    except TASPluginException:
        logger.exception(
            "Could not create the report because of the error below"
        )
        return


def _create_tas_report_for(user, tacc_username, tacc_project_name, end_date):
    """
    Create a new report
    """
    if not end_date:
        raise TASPluginException("Explicit end date required")
    if not user:
        raise TASPluginException("User missing")
    if not tacc_username:
        raise TASPluginException("TACC Username missing")
    if not tacc_project_name:
        raise TASPluginException("OpenStack/TACC Project missing")

    last_report = TASAllocationReport.objects.filter(
        project_name=tacc_project_name,
        user=user
    ).order_by('end_date').last()
    if not last_report:
        start_date = user.date_joined
    else:
        start_date = last_report.end_date

    compute_used = total_usage(
        user.username, start_date,
        allocation_source_name=tacc_project_name,
        end_date=end_date)

    if compute_used < 0:
        raise TASPluginException(
            "Compute usage was not accurately calculated for user:%s for start_date:%s and end_date:%s"
            % (user, start_date, end_date))

    new_report = TASAllocationReport.objects.create(
        user=user,
        username=tacc_username,
        project_name=tacc_project_name,
        compute_used=compute_used,
        start_date=start_date,
        end_date=end_date,
        tacc_api=settings.TACC_API_URL)
    logger.info("Created New Report:%s" % new_report)
    return new_report
