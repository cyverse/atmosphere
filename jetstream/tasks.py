import logging

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from jetstream.models import TASAllocationReport
from jetstream.allocation import get_project_allocations

from .exceptions import TASPluginException


logger = logging.getLogger(__name__)


def xsede_tacc_map(username):
    """
    Given a XSEDE username, query the XSEDEAPI to produce a TACC username
    """
    #FIXME this is wrong
    return username

def create_reports():
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    User = get_user_model()
    all_reports = []
    for user in User.objects.all():
        tacc_username = xsede_tacc_map(user.username)
        project_allocations = get_project_allocations(tacc_username)
        for allocation in project_allocations:
            # This is the one you want to charge
            tacc_project_name = allocation['project']
            project_reports = _create_tas_reports_for(user, tacc_username, tacc_project_name)
            all_reports.extend(project_reports)
    return all_reports


def _create_tas_reports_for(user, tacc_username, tacc_project_name):
    all_reports = []
    if not hasattr(user, 'current_identities'):
        raise TASPluginException(
            "User %s does not have attribute 'current_identities'" % user)
    for ident in user.current_identities:
        cred_project_name = ident.get_credential('ex_project_name')
        identifier = "%s - %s" % (ident.provider.location, cred_project_name)  # Ex: Jetstream - TACC - TG-TRA160003
        if cred_project_name != tacc_project_name:
            pass
        last_report = TASAllocationReport.objects.filter(
            project_name=tacc_project_name,
            scheduler_id=identifier,
            user=user, success=True
            ).order_by('report_date').last()
        report = _create_tas_report(
            last_report, ident, user,
            tacc_username, tacc_project_name,
            scheduler_id=identifier)
        all_reports.append(report)
    return all_reports


def _create_tas_report(last_report, identity, user,
                       tacc_username, tacc_project, scheduler_id=None):
    """
    Create a new report
    """
    if not user:
        raise TASPluginException("User missing")
    if not tacc_username:
        raise TASPluginException("TACC Username missing")
    if not tacc_project:
        raise TASPluginException("OpenStack/TACC Project missing")
    if not identity:
        raise TASPluginException("Identity missing")
    if not last_report:
        start_date = user.date_joined
    else:
        start_date = last_report.end_date
    end_date = timezone.now()
    compute_used = identity.total_usage(start_date, end_date)
    if compute_used < 0:
        raise TASPluginException(
            "Identity was not able to accurately calculate usage: %s"
            % identity)
    new_report = TASAllocationReport.objects.create(
        user=user, username=tacc_username, project_name=tacc_project,
        compute_used=compute_used,
        queue_name="Jetstream - User:%s" % user.username, scheduler_id=scheduler_id,
        start_date=start_date, end_date=end_date, tacc_api=settings.TACC_API_URL)
    logger.info("Created new report %s" % new_report)
    return new_report

"""
Methods yet to be created
#1: Enforcing the allocation strategy when AU are :100:% consumed.
#2: Mapping from XSede to TACC
"""
