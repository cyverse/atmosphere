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
from service.allocation_logic import create_report
from core.models.user import AtmosphereUser

from .models import TASAllocationReport
from .allocation import (
    TASAPIDriver, fill_allocation_sources,
    fill_user_allocation_sources
)

from .exceptions import TASPluginException


logger = logging.getLogger(__name__)


@task(name="monitor_jetstream_allocation_sources",
     )
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
    driver = TASAPIDriver()
    end_date = timezone.now()
    for item in user_allocation_list:
        allocation_id = item.allocation_source.source_id
        tacc_username = driver.get_tacc_username(item.user)
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
    if 'jetstream' not in settings.INSTALLED_APPS:
        return
    logger.info("Reporting: Begin creating reports")
    create_reports()
    logger.info("Reporting: Completed, begin sending reports")
    send_reports()
    logger.info("Reporting: Reports sent")



def send_reports():
    failed_reports = 0
    reports_to_send = TASAllocationReport.objects.filter(success=False).order_by('user__username','start_date')
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
def update_snapshot():
    if not settings.USE_ALLOCATION_SOURCE:
        return False
    allocation_source_total_compute = {}
    allocation_source_total_burn_rate = {}
    end_date = timezone.now()
    for source in AllocationSource.objects.order_by('source_id'):
        # iterate over user + allocation_source combo
        for user_allocation_source in UserAllocationSource.objects.filter(allocation_source__exact=source.id).order_by('user__username'):
            user = user_allocation_source.user
            # determine end date and start date using last snapshot
            start_date = user.date_joined
            # calculate compute used and burn rate for the user and allocation source combo
            compute_used, burn_rate = total_usage(user.username,start_date,allocation_source_name=source.name,end_date=end_date,burn_rate=True)

            allocation_source_total_compute[source.name] = allocation_source_total_compute.get(source.name,0) + compute_used
            allocation_source_total_burn_rate[source.name] = allocation_source_total_burn_rate.get(source.name,0) + burn_rate

            payload_ubr = {"allocation_source_id":source.source_id, "username":user.username, "burn_rate":burn_rate, "compute_used":compute_used}
            EventTable.create_event("user_allocation_snapshot_changed", payload_ubr, user.username)
        compute_used_total = allocation_source_total_compute.get(source.name,0)
        global_burn_rate = allocation_source_total_burn_rate.get(source.name,0)
        if compute_used_total != 0:
            logger.info("Total usage for AllocationSource %s (%s-%s) = %s (Burn Rate: %s)" % (source.name, start_date, end_date, compute_used_total, global_burn_rate))
        payload_as = { 
            "allocation_source_id":source.source_id, 
            "compute_used":compute_used_total,
            "global_burn_rate":global_burn_rate
        }
        EventTable.create_event("allocation_source_snapshot", payload_as,source.name)
    return True

@task(name="update_snapshot")
def update_snapshot2():
    if not settings.USE_ALLOCATION_SOURCE:
        return False
    allocation_source_total_compute = {}
    allocation_source_total_burn_rate = {}
    end_date = timezone.now()
    start_date = '2016-09-01T00:00+00:00'
    all_data = create_report(start_date, end_date)
    tas_api_obj = TASAPIDriver()
    allocation_source_usage_from_tas = tas_api_obj.get_all_projects()
    for source in AllocationSource.objects.order_by('source_id'):
        compute_used_total = 0
        global_burn_rate = 0
        for user in AtmosphereUser.objects.all():
            compute_used, burn_rate = usage_for_user_allocation_snapshot(all_data, user.username, source.name)
            user_snapshot_changes(source, user, compute_used, burn_rate)
            compute_used_total += compute_used
            global_burn_rate += burn_rate
        allocation_snapshot_changes(source, allocation_source_usage_from_tas, global_burn_rate)
    return True

def usage_for_user_allocation_snapshot(data, username, allocation_source_name):
    total_allocation = 0
    burn_rate = 0
    for row in data:
        if row['allocation_source'] == allocation_source_name and row['username']==username:
            total_allocation += row['applicable_duration']
            burn_rate = row['burn_rate']
    return round(total_allocation/3600.0,2),burn_rate

def allocation_snapshot_changes(allocation_source,tas_api_usage_data, global_burn_rate):
    """
    The method should result in an up-to-date snapshot of AllocationSource usage.
    """
    compute_used = [i['allocations'][-1]['computeUsed'] for i in tas_api_usage_data if i['chargeCode'] == allocation_source.name][-1]
    try:
        snapshot = AllocationSourceSnapshot.objects.get(
            allocation_source=allocation_source
        )
        snapshot.compute_used = compute_used
        snapshot.global_burn_rate = global_burn_rate
        snapshot.save()
    except AllocationSourceSnapshot.DoesNotExist:
        snapshot = AllocationSourceSnapshot.objects.create(
            allocation_source=allocation_source,
            compute_used=compute_used,
            global_burn_rate=global_burn_rate
        )
    return snapshot


def user_snapshot_changes(allocation_source, user, compute_used, burn_rate):
    """
    The method should result in an up-to-date compute used + burn rate snapshot for the specific User+AllocationSource
    """

    try:
        snapshot = UserAllocationSnapshot.objects.get(
                allocation_source=allocation_source,
                user=user,
            )
        snapshot.burn_rate = burn_rate
        snapshot.compute_used = compute_used
        snapshot.save()
    except UserAllocationSnapshot.DoesNotExist:
        snapshot = UserAllocationSnapshot.objects.create(
                allocation_source=allocation_source,
                user=user,
                burn_rate=burn_rate,
                compute_used=compute_used
            )
    return snapshot