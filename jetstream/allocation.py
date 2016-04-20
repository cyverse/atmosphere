import logging

from django.conf import settings

from .exceptions import TASAPIException
from .api import tacc_api_post, tacc_api_get


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


def get_project_allocations(username, tacc_api=None):
    if not tacc_api:
        tacc_api = settings.TACC_API_URL
    path = '/v1/projects/username/%s' % username
    url_match = tacc_api + path
    resp, data = tacc_api_get(url_match)
    project_allocations = {}
    try:
        if data['status'] != 'success':
            raise TASAPIException(
                "API is returning an unexpected status: %s"
                % data['status'])
        projects = data['result']
        for project in projects:
            project_title = project['title']
            allocations = project['allocations']
            for allocation in allocations:
                if allocation['resource'].lower() == 'jetstream':
                    project_allocations[project_title] = allocation
        return project_allocations
    except ValueError as exc:
        raise TASAPIException("JSON Decode error -- %s" % exc)


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
