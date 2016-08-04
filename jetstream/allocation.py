import logging

from django.conf import settings

from .exceptions import TASAPIException
from .api import tacc_api_post, tacc_api_get
from core.models.allocation_source import AllocationSource, UserAllocationSource

logger = logging.getLogger(__name__)


def get_username_from_xsede(xsede_username, tacc_api=None):
    if not tacc_api:
        tacc_api = settings.TACC_API_URL
    path = '/v1/users/xsede/%s' % xsede_username
    url_match = tacc_api + path
    resp, data = tacc_api_get(url_match)
    try:
        if data['status'] != 'success':
            raise TASAPIException(
                "NO valid username found for %s" % xsede_username)
        tacc_username = data['result']
        return tacc_username
    except ValueError as exc:
        raise TASAPIException("JSON Decode error -- %s" % exc)



def get_all_allocations(tacc_api=None, resource_name='Jetstream'):
    """
    """
    if not tacc_api:
        tacc_api = settings.TACC_API_URL
    path = '/v1/allocations/resource/%s' % resource_name
    allocations = {}
    url_match = tacc_api + path
    resp, data = tacc_api_get(url_match)
    try:
        _validate_tas_data(data)
        allocations = data['result']
        return allocations
    except ValueError as exc:
        raise TASAPIException("JSON Decode error -- %s" % exc)

def get_all_projects(tacc_api=None, resource_name='Jetstream'):
    """
    """
    if not tacc_api:
        tacc_api = settings.TACC_API_URL
    path = '/v1/projects/resource/%s' % resource_name
    url_match = tacc_api + path
    resp, data = tacc_api_get(url_match)
    try:
        _validate_tas_data(data)
        projects = data['result']
        return projects
    except ValueError as exc:
        raise TASAPIException("JSON Decode error -- %s" % exc)


def _get_tacc_user(user):
    try:
        tacc_user = get_username_from_xsede(
            user.username)
    except:
        logger.info("User: %s has no tacc username" % user.username)
        tacc_user = user.username
    return tacc_user


def _validate_tas_data(data):
    if not data or 'status' not in data or 'result' not in data:
        raise TASAPIException(
            "API is returning a malformed response - "
            "Expected json object including "
            "a 'status' key and a 'result' key. - "
            "Received: %s" % data)
    if data['status'] != 'success':
        raise TASAPIException(
            "API is returning an unexpected status %s - "
            "Received: %s"
            % (data['status'], data)
        )
    return True


def get_user_allocations(username, tacc_api=None, resource_name='Jetstream', raise_exception=True):
    if not tacc_api:
        tacc_api = settings.TACC_API_URL
    path = '/v1/projects/username/%s' % username
    url_match = tacc_api + path
    resp, data = tacc_api_get(url_match)
    user_allocations = []
    try:
        _validate_tas_data(data)
        projects = data['result']
        for project in projects:
            allocations = project['allocations']
            for allocation in allocations:
                if allocation['resource'] == resource_name:
                    user_allocations.append( (project, allocation) )
        return user_allocations
    except ValueError as exc:
        if raise_exception:
            raise TASAPIException("JSON Decode error -- %s" % exc)
        logger.info( exc)
    except Exception as exc:
        if raise_exception:
            raise
        logger.info( exc)
    return None


def report_project_allocation(username, project_name, su_total, start_date, end_date, queueName=None, schedulerId=None, resourceName=None, tacc_api=None):
    """
    Send back a report
    """
    # FIXME: Find a use for 'queueName' and 'schedulerId'
    if not queueName:
        queueName = "Atmosphere Queue"  # IDEA: queueName = provider.location
    if not schedulerId:
        schedulerId = "use.jetstream-cloud.org"  # IDEA: schedulerId = provider, or even instance UUID? Granularity?
    if not resourceName:
        resourceName = "Jetstream"  # FIXME: Move to settings
    if not type(su_total) in [int, float]:
        raise Exception("SU total should be integer or float")

    post_data = {
        "sus": su_total,  # NOTE: This is likely to change in future v.
        "username": username,
        "project": project_name,
        # These things could be more useful in a final version, see IDEAs above
        "queueName": queueName,
        "resource": resourceName,
        "schedulerId": schedulerId,
        # Ex date format: "2014-12-01T19:25:43"
        "queueUTC": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "startUTC": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "endUTC": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    if not tacc_api:
        tacc_api = settings.TACC_API_URL

    path = '/v1/jobs'
    url_match = tacc_api + path
    resp = tacc_api_post(url_match, post_data)
    try:
        data = resp.json()
        resp_status = data['status']
    except ValueError:
        exc_message = ("Invalid Response - Expected 'status' in the json response: %s" % (resp.text,))
        logger.exception(exc_message)
        raise ValueError(exc_message)

    if resp_status != 'success' or resp.status_code != 200:
        exc_message = ("Invalid Response - Expected 200 and 'success' response: %s - %s" % (resp.status_code, resp_status))
        logger.exception(exc_message)
        raise Exception(exc_message)

    return data

def get_or_create_allocation_source(api_allocation, update_source=False):
    try:
        title = "%s: %s" % (api_allocation['project'], api_allocation['justification'])
        source_id = api_allocation['id']
        compute_allowed = int(api_allocation['computeAllocated'])
    except:
        raise#raise TASAPIException("Malformed API Allocation - %s" % api_allocation)

    try:
        source = AllocationSource.objects.get(
            name=title,
            source_id=source_id
        )
        if update_source and compute_allowed != source.compute_allowed:
            source.compute_allowed = compute_allowed
            source.save()
        return source, False
    except AllocationSource.DoesNotExist:
        source = AllocationSource.objects.create(
            name=title,
            compute_allowed = compute_allowed,
            source_id=source_id
        )
        return source, True


def fill_allocation_sources(force_update=False):
    allocations = get_all_allocations()
    create_list = []
    for api_allocation in allocations:
        obj, created = get_or_create_allocation_source(
            api_allocation, update_source=force_update)
        if created:
            create_list.append(obj)
    return len(create_list)


def fill_user_allocation_sources():
    from core.models import AtmosphereUser
    for user in AtmosphereUser.objects.order_by('id'):
        fill_user_allocation_source_for(user, force_update=True)


def fill_user_allocation_source_for(user, force_update=False):
    """
    FIXME: Hook this function into calls for new AtmosphereUser objects. We need to know the users valid projects immediately after we create the AtmosphereUser account :)
    """
    tacc_user = _get_tacc_user(user)
    logger.info( "%s -> %s" % (user, tacc_user))
    user_allocations = get_user_allocations(
        tacc_user, raise_exception=False)
    if not user_allocations:
        logger.info( "User %s does not have any valid allocations" % tacc_user)
        return
    for (project, api_allocation) in user_allocations:
        allocation_source, _ = get_or_create_allocation_source(
            api_allocation, update_source=force_update)
        resource, _ = UserAllocationSource.objects.get_or_create(
            allocation_source=allocation_source,
            user=user)
