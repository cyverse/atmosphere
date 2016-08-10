import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from celery.decorators import task
from core.models.allocation_source import total_usage
from core.models.allocation_source import (
    UserAllocationSource, AllocationSourceSnapshot,
    AllocationSource, UserAllocationSnapshot
)
from core.models.event_table import EventTable

from .models import TASAllocationReport
from .allocation import (
    TASAPIDriver, fill_allocation_sources,
    fill_user_allocation_sources
)

from .exceptions import TASPluginException


logger = logging.getLogger(__name__)


def monitor_jetstream_allocation_sources():
    """
    Queries the TACC API for Jetstream allocation sources
    Adds each new source (And user association) to the DB.
    """
    new_sources = fill_allocation_sources(True)
    fill_user_allocation_sources()
    return new_sources


def create_reports():
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    user_allocation_list = UserAllocationSource.objects.all()
    all_reports = []
    driver = TASAPIDriver()
    end_date = timezone.now()
    for item in user_allocation_list:
        allocation_id = item.allocation_source.source_id
        tacc_username = driver._get_tacc_user(item.user)
        project_name = driver.get_allocation_project_name(allocation_id)
        try:
            project_report = _create_tas_report_for(
                item.user,
                tacc_username,
                project_name,
                end_date)
        except TASPluginException:
            logger.exception(
                "Could not create the report because of the error below"
            )
            continue
        all_reports.append(project_report)
    return all_reports


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
        user, start_date,
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
    if 'jetstream' not in settings.INSTALLED_APPS:
        return
    create_reports()
    send_reports()


def send_reports():
    for tas_report in TASAllocationReport.objects.filter(success=False):
        tas_report.send()

@task(name="update_snapshot")
def update_snapshot():
    if not settings.USE_ALLOCATION_SOURCE:
        return
    allocation_source_total_compute = {}
    allocation_source_total_burn_rate = {}
    end_date = timezone.now()
    for source in AllocationSource.objects.all():
        # iterate over user + allocation_source combo
        for user_allocation_source in UserAllocationSource.objects.filter(allocation_source__exact=source.id):
            user = user_allocation_source.user
            # determine end date and start date using last snapshot
            start_date = user.date_joined
            # calculate compute used and burn rate for the user and allocation source combo
            compute_used, burn_rate = total_usage(user,start_date,allocation_source=source.name,end_date=end_date,burn_rate=True)

            allocation_source_total_compute[source.name] = allocation_source_total_compute.get(source.name,0) + compute_used
            allocation_source_total_burn_rate[source.name] = allocation_source_total_burn_rate.get(source.name,0) + burn_rate

            payload_ubr = {"allocation_source_id":source.source_id, "username":user.username, "burn_rate":burn_rate, "compute_used":compute_used}
            EventTable.create_event("user_allocation_snapshot_changed", payload_ubr, user.username)

        payload_as = { 
            "allocation_source_id":source.source_id, 
            "compute_used":allocation_source_total_compute[source.name],
            "global_burn_rate":allocation_source_total_burn_rate[source.name]
        }
        EventTable.create_event("allocation_source_snapshot", payload_as,source.name)
