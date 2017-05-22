import logging

from business_rules import run_all
from celery.decorators import task
from django.conf import settings
from django.utils import timezone

from core.models import EventTable, AtmosphereUser
from core.models.allocation_source import (
    UserAllocationSource, AllocationSourceSnapshot,
    AllocationSource, UserAllocationSnapshot
)
from core.models.allocation_source import total_usage
from cyverse_allocation.cyverse_rules_engine_setup import CyverseTestRenewalVariables, CyverseTestRenewalActions, \
    cyverse_rules
from .allocation import (TASAPIDriver, fill_user_allocation_sources, select_valid_allocation)
from .exceptions import TASPluginException
from .models import TASAllocationReport

logger = logging.getLogger(__name__)


@task(name="monitor_jetstream_allocation_sources")
def monitor_jetstream_allocation_sources():
    """
    Queries the TACC API for Jetstream allocation sources
    Adds each new source (And user association) to the DB.
    """
    resources = fill_user_allocation_sources()
    return resources


def create_reports():
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    user_allocation_list = UserAllocationSource.objects.all()
    all_reports = []
    end_date = timezone.now()
    last_report_date = TASAllocationReport.objects.order_by('end_date')

    if not last_report_date:
        last_report_date = end_date
    else:
        last_report_date = last_report_date.last().end_date

    for item in user_allocation_list:
        allocation_name = item.allocation_source.name
        project_report = _create_reports_for(item.user, allocation_name, end_date)
        if project_report:
            all_reports.append(project_report)

    # Take care of Deleted Users

    # filter user_allocation_source_removed events which are created after the last report date

    for event in EventTable.objects.filter(name="user_allocation_source_deleted",
                                           timestamp__gte=last_report_date).order_by('timestamp'):

        user = AtmosphereUser.objects.get(username=event.entity_id)
        allocation_name = event.payload['allocation_source_name']
        end_date = event.timestamp
        project_report = _create_reports_for(user, allocation_name, end_date)
        if project_report:
            all_reports.append(project_report)
    return all_reports


def _create_reports_for(user, allocation_name, end_date):
    driver = TASAPIDriver()
    tacc_username = driver.get_tacc_username(user)
    if not tacc_username:
        logger.error("No TACC username for user: '{}' which came from allocation id: {}".format(user,
                                                                                                allocation_name))
        return
    project_name = driver.get_allocation_project_name(allocation_name)
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
            "Compute usage was not accurately calculated for user:%s"
            % user)

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


@task(name="report_allocations_to_tas")
def report_allocations_to_tas():
    logger.info("Reporting: Begin creating reports")
    create_reports()
    logger.info("Reporting: Completed, begin sending reports")
    send_reports()
    logger.info("Reporting: Reports sent")


def send_reports():
    failed_reports = 0
    reports_to_send = TASAllocationReport.objects.filter(success=False).order_by('user__username', 'start_date')
    count = reports_to_send.count()
    for tas_report in reports_to_send:
        try:
            tas_report.send()
        except TASPluginException:
            logger.exception(
                "Could not send the report because of the error below"
            )
            failed_reports += 1
            continue
    if failed_reports != 0:
        raise Exception("%s/%s reports failed to send to TAS" % (failed_reports, count))


@task(name="update_snapshot")
def update_snapshot(start_date=None, end_date=None):
    end_date = end_date or timezone.now()
    # TODO: Read this start_date from last 'reset event' for each allocation source
    start_date = start_date or '2016-09-01 00:00:00.0-05'

    tas_api_obj = TASAPIDriver()
    allocation_source_usage_from_tas = tas_api_obj.get_all_projects()

    for project in allocation_source_usage_from_tas:
        total_burn_rate = 0
        allocation_source_name = project['chargeCode']
        try:
            allocation_source = AllocationSource.objects.filter(name=allocation_source_name).order_by('id').last()

            if not allocation_source:
                continue

            created_or_updated_event = EventTable.objects.filter(
                name='allocation_source_created_or_renewed',
                payload__allocation_source_name=allocation_source.name
            ).order_by('timestamp').last()

            if created_or_updated_event:
                # if renewed, change ignore old allocation usage
                start_date = created_or_updated_event.payload['start_date']

            for user in allocation_source.all_users:
                compute_used, burn_rate = total_usage(user.username, start_date,
                                                      allocation_source_name=allocation_source.name,
                                                      end_date=end_date,
                                                      burn_rate=True)
                total_burn_rate += burn_rate
                UserAllocationSnapshot.objects.update_or_create(
                    allocation_source_id=allocation_source.id,
                    user_id=user.id,
                    defaults={
                        'compute_used': compute_used,
                        'burn_rate': burn_rate
                    }
                )

        except KeyError:
            # This allocation source does not exist in our database yet. Create it? Skip for now.
            continue
        valid_allocation = select_valid_allocation(project['allocations'])
        compute_used = valid_allocation['computeUsed'] if valid_allocation else 0
        AllocationSourceSnapshot.objects.update_or_create(
            allocation_source_id=allocation_source.id,
            defaults={
                'compute_used': compute_used,
                'global_burn_rate': total_burn_rate
            }
        )
    return True