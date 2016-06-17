import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import TASAllocationReport
from .allocation import get_project_allocations, get_username_from_xsede

from .exceptions import TASPluginException


logger = logging.getLogger(__name__)


def xsede_tacc_map(username):
    """
    Given a XSEDE username, query the XSEDEAPI to produce a TACC username
    """
    #FIXME this is wrong
    return get_username_from_xsede(username)

def create_reports():
    """
    GO through the list of all users or all providers
    For each username, get an XSede API map to the 'TACC username'
    if 'TACC username' includes a jetstream resource, create a report
    """
    User = get_user_model()
    all_reports = []
    for user in User.objects.filter(username__in=['sgregory',]):
        tacc_username = xsede_tacc_map(user.username)
        project_allocations = get_project_allocations(tacc_username)
        #FIXME: User 'sgregory' has two allocations: Project:jetstream-admin && Project:TG-TRA160003
        # Current implementation charges *both* projects.
        # Future fix: the allocation + project_name == the allocation attached to core.Project Proj.
        # Only those associated instances and volumes are charged.
        for project_name, allocation in project_allocations.items():
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
    if not identity:
        raise TASPluginException("Identity missing")
    if not tacc_username:
        raise TASPluginException("TACC Username missing")
    if not tacc_project:
        raise TASPluginException("OpenStack/TACC Project missing")
    if not identity:
        raise TASPluginException("Identity missing")
    if not scheduler_id:
        scheduler_id = "%s + %s" % (identity.provider.location, tacc_project)

    last_report = TASAllocationReport.objects.filter(
        project_name=tacc_project,
        scheduler_id=scheduler_id,
        user=user
        ).order_by('end_date').last()
    if not last_report:
        start_date = user.date_joined
    else:
        start_date = last_report.end_date
    end_date = timezone.now()

    #NOTE: This is where the magic happens.
    compute_used = identity.total_usage(start_date, end_date)
    #NOTE: Future version change
    #project = user.shared_projects(tacc_project)
    #compute_used = project.total_usage(identity, start_date, end_date)
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
    # NOTE:sending these reports will happen all at once, in a different task.
    return new_report

"""
Methods yet to be created
#1: Enforcing the allocation strategy when AU are :100:% consumed.
#2: Mapping from XSede to TACC
"""
