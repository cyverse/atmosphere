import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from celery.decorators import task
from core.models.allocation_source import total_usage
from core.models.allocation_source import UserAllocationSource, AllocationSourceSnapshot, AllocationSource, UserAllocationBurnRateSnapshot
from core.models.event_table import EventTable

from .models import TASAllocationReport
from .allocation import get_username_from_xsede, fill_allocation_sources

from .exceptions import TASPluginException


logger = logging.getLogger(__name__)


def xsede_tacc_map(username):
    """
    Given a XSEDE username, query the XSEDEAPI to produce a TACC username
    """
    #FIXME this is wrong
    return get_username_from_xsede(username)

def monitor_jetstream_allocation_sources():
    """
    Queries the TACC API for Jetstream allocations
    """
    new_sources = fill_allocation_sources(True)
    return new_sources

def create_reports():
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    user_allocation_list = UserAllocationSource.objects.all()
    all_reports = []
    for item in user_allocation_list:
        project_reports = _create_tas_reports_for(
            item.user,
            item.user.username,
            item.allocation_source.name)
        all_reports.extend(project_reports)
    return all_reports


def _create_tas_reports_for(user, tacc_username, tacc_project_name):
    all_reports = []
    if not hasattr(user, 'current_identities'):
        raise TASPluginException(
            "User %s does not have attribute 'current_identities'" % user)
    #for ident in user.current_identities:
    ident = None if len(user.current_identities)<1 else user.current_identities[0]
    report = _create_tas_report(
            ident, user,
            tacc_username, tacc_project_name,
    )
    all_reports.append(report)
    return all_reports


def _create_tas_report(identity, user,
                       tacc_username, tacc_project, scheduler_id=None
                       ):
    """
    Create a new report
    """
    if not user:
        raise TASPluginException("User missing")
    #if not identity:
        #raise TASPluginException("Identity missing")
  
    if not tacc_username:
        raise TASPluginException("TACC Username missing")
    if not tacc_project:
        raise TASPluginException("OpenStack/TACC Project missing")
    #if not identity:
        #raise TASPluginException("Identity missing")
    if not scheduler_id:
        if not identity:
            scheduler_id = "n/a"
        else:
            scheduler_id = "%s + %s" % (identity.provider.location, tacc_project)

    last_report = TASAllocationReport.objects.filter(
        project_name=tacc_project,
        #scheduler_id=scheduler_id,
        user=user
        ).order_by('end_date').last()
    if not last_report:
        start_date = user.date_joined
    else:
        start_date = last_report.end_date
    end_date = timezone.now()

    compute_used = total_usage(user,start_date,allocation_source=tacc_project,end_date=end_date)

    if compute_used < 0:
        raise TASPluginException(
            "Identity was not able to accurately calculate usage: %s"
            % identity)

    new_report = TASAllocationReport.objects.create(
        user=user, username=tacc_username, project_name=tacc_project,
        compute_used=compute_used,
        queue_name="Jetstream - User:%s" % user.username,
        scheduler_id=scheduler_id,
        start_date=start_date,
        end_date=end_date,
        tacc_api=settings.TACC_API_URL)
    logger.info("Created New Report:%s" % new_report)
    return new_report

@task(name="create_report")
def create_report():
    create_reports()
    #write code to post data to TACC api
    send_reports()


def send_reports():
    for tas_report in TASAllocationReport.objects.filter(success=False):
        tas_report.send()

@task(name="update_snapshot")
def update_snapshot():
    allocation_source_total_compute = {}
    allocation_source_total_burn_rate = {}
    for source in AllocationSource.objects.all():
         # iterate over user + allocation_source combo
         last_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=source).first()
         for user_allocation_source in UserAllocationSource.objects.filter(allocation_source__exact=source.id):
             user = user_allocation_source.user
             # determine end date and start date using last snapshot
             if not last_snapshot:
                 start_date = user.date_joined
             else:
                 start_date = last_snapshot.updated
             end_date = timezone.now()
             # calculate compute used and burn rate for the user and allocation source combo
             compute_used, burn_rate = total_usage(user,start_date,allocation_source=source.name,end_date=end_date,burn_rate=True)

             allocation_source_total_compute[source.name] = allocation_source_total_compute.get(source.name,0) + compute_used
             allocation_source_total_burn_rate[source.name] = allocation_source_total_burn_rate.get(source.name,0) + burn_rate

             payload_ubr = {"allocation_source_id":source.source_id, "username":user.username, "burn_rate":burn_rate}
             EventTable.create_event("user_burn_rate_changed", payload_ubr, user.username)

         payload_as = {"allocation_source_id":source.source_id, "compute_used":allocation_source_total_compute[source.name],"global_burn_rate":allocation_source_total_burn_rate[source.name]}
         EventTable.create_event("allocation_source_snapshot", payload_as,source.name)
