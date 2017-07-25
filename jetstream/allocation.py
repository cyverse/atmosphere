import uuid
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from dateutil.parser import parse

from .exceptions import TASAPIException, NoTaccUserForXsedeException, NoAccountForUsernameException
#FIXME: Next iteration, move this into the driver.
from .tas_api import tacc_api_post, tacc_api_get
from core.models import EventTable
from core.models.allocation_source import AllocationSource, UserAllocationSource

from threepio import logger


class TASAPIDriver(object):
    tacc_api = None
    tacc_username = None
    tacc_password = None
    allocation_list = []
    project_list = []
    user_project_list = []
    username_map = {}

    def __init__(self, tacc_api=None, tacc_username=None, tacc_password=None,
                 resource_name='Jetstream'):
        if not tacc_api:
            tacc_api = settings.TACC_API_URL
        if not tacc_username:
            tacc_username = settings.TACC_API_USER
        if not tacc_password:
            tacc_password = settings.TACC_API_PASS
        self.tacc_api = tacc_api
        self.tacc_username = tacc_username
        self.tacc_password = tacc_password
        self.resource_name = resource_name

    def clear_cache(self):
        self.user_project_list = []
        self.project_list = []
        self.allocation_list = []
        self.username_map = {}

    def get_all_allocations(self):
        if not self.allocation_list:
            self.allocation_list = self._get_all_allocations()
        return self.allocation_list

    def get_all_projects(self):
        if not self.project_list:
            self.project_list = self._get_all_projects()
        return self.project_list

    def get_tacc_username(self, user, raise_exception=False):
        if self.username_map.get(user.username):
            return self.username_map[user.username]
        tacc_user = None
        try:
            tacc_user = self._xsede_to_tacc_username(
                user.username)
        except NoTaccUserForXsedeException:
            logger.exception('User: %s has no TACC username', user.username)
            if raise_exception:
                raise
        except TASAPIException:
            logger.exception('Some exception happened while getting TACC username for user: %s', user.username)
            if raise_exception:
                raise
        else:
            self.username_map[user.username] = tacc_user
        return tacc_user

    def find_projects_for(self, tacc_username):
        if not self.user_project_list:
            self.user_project_list = self.get_all_project_users()
        if not tacc_username:
            return self.user_project_list
        filtered_user_list = [p for p in self.user_project_list if tacc_username in p['users']]
        return filtered_user_list

    def find_allocations_for(self, tacc_username):
        api_projects = self.find_projects_for(tacc_username)
        allocations = []
        for api_project in api_projects:
            api_allocation = select_valid_allocation(api_project['allocations'])
            if not api_allocation:
                logger.error("API shows no valid allocation exists for project %s" % api_project)
                continue
            allocations.append(api_allocation)
        return allocations

    def get_all_project_users(self):
        if not self.user_project_list:
            self.project_list = self._get_all_projects()
            for project in sorted(self.project_list, key=lambda p: p['id']):
                project_users = self.get_project_users(project['id'])
                project['users'] = project_users
            self.user_project_list = self.project_list
        return self.user_project_list

    def _xsede_to_tacc_username(self, xsede_username):
        path = '/v1/users/xsede/%s' % xsede_username
        url_match = self.tacc_api + path
        resp, data = tacc_api_get(url_match, self.tacc_username, self.tacc_password)
        try:
            status = data.get('status')
            message = data.get('message')
            if status == 'error' and message == 'No user found for XSEDE username {}'.format(xsede_username):
                raise NoTaccUserForXsedeException('No valid username found for %s' % xsede_username)
            if status == 'error':
                raise TASAPIException('Error while getting username for %s' % xsede_username)
            tacc_username = data['result']
            return tacc_username
        except ValueError as exc:
            raise TASAPIException("JSON Decode error -- %s" % exc)


    def report_project_allocation(self, report_id, username, project_name, su_total, start_date, end_date, queue_name, scheduler_id):
        """
        Send back a report
        """
        if not type(su_total) in [int, float]:
            raise Exception("SU total should be integer or float")

        post_data = {
            "sus": su_total,
            "username": username,
            "project": project_name,
            "queueName": queue_name,
            "resource": self.resource_name,
            "schedulerId": scheduler_id,
            # Ex date format: "2014-12-01T19:25:43"
            "queueUTC": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "startUTC": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "endUTC": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        path = '/v1/jobs'
        url_match = self.tacc_api + path
        # logger.debug("TAS_REQ: %s - POST - %s" % (url_match, post_data))
        resp = tacc_api_post(url_match, post_data, self.tacc_username, self.tacc_password)
        # logger.debug("TAS_RESP: %s" % resp.__dict__)  # Overkill?
        try:
            data = resp.json()
            #logger.debug("TAS_RESP - Data: %s" % data)
            resp_status = data['status']
        except ValueError:
            exc_message = ("Report %s produced an Invalid Response - Expected 'status' in the json response: %s" % (report_id, resp.text,))
            logger.exception(exc_message)
            raise ValueError(exc_message)
    
        if resp_status != 'success' or resp.status_code != 200:
            exc_message = ("Report %s produced an Invalid Response - Expected 200 and 'success' response: %s - %s" % (report_id, resp.status_code, resp_status))
            logger.exception(exc_message)
            raise Exception(exc_message)
    
        return data

    def get_allocation_project_id(self, allocation_name):
        allocation = self.get_allocation(allocation_name)
        if not allocation:
            return
        return allocation['projectId']

    def get_allocation_project_name(self, allocation_name):
        allocation = self.get_allocation(allocation_name)
        if not allocation:
            return
        return allocation['project']

    def get_project(self, project_id):
        filtered_list = [
            p for p in self.get_all_projects()
            if str(p['id']) == str(project_id)]
        if len(filtered_list) > 1:
            logger.error(">1 value found for project %s" % project_id)
        if filtered_list:
            return filtered_list[0]
        return None

    def get_allocation(self, allocation_name):
        filtered_list = [
            a for a in self.get_all_allocations()
            if str(a['project']) == str(allocation_name)]
        if len(filtered_list) > 1:
            logger.error(">1 value found for allocation %s" % allocation_name)
        if filtered_list:
            return filtered_list[0]
        return None

    def _get_all_allocations(self):
        """
        """
        path = '/v1/allocations/resource/%s' % self.resource_name
        allocations = {}
        url_match = self.tacc_api + path
        resp, data = tacc_api_get(url_match, self.tacc_username, self.tacc_password)
        try:
            _validate_tas_data(data)
            allocations = data['result']
            return allocations
        except ValueError as exc:
            raise TASAPIException("JSON Decode error -- %s" % exc)

    def _get_all_projects(self):
        """
        """
        path = '/v1/projects/resource/%s' % self.resource_name
        url_match = self.tacc_api + path
        resp, data = tacc_api_get(url_match, self.tacc_username, self.tacc_password)
        try:
            _validate_tas_data(data)
            projects = data['result']
            return projects
        except ValueError as exc:
            raise TASAPIException("JSON Decode error -- %s" % exc)

    def get_project_users(self, project_id, raise_exception=True):
        path = '/v1/projects/%s/users' % project_id
        url_match = self.tacc_api + path
        resp, data = tacc_api_get(url_match, self.tacc_username, self.tacc_password)
        user_names = []
        try:
            _validate_tas_data(data)
            users = data['result']
            for user in users:
                username = user['username']
                user_names.append(username)
            return user_names
        except ValueError as exc:
            if raise_exception:
                raise TASAPIException("JSON Decode error -- %s" % exc)
            logger.info(exc)
        except Exception as exc:
            if raise_exception:
                raise
            logger.info(exc)
        return user_names

    

    def get_user_allocations(self, username, include_expired=False, raise_exception=True):
        path = '/v1/projects/username/%s' % username
        url_match = self.tacc_api + path
        resp, data = tacc_api_get(url_match, self.tacc_username, self.tacc_password)
        user_allocations = []
        try:
            _validate_tas_data(data)
            projects = data['result']
            for project in projects:
                api_allocations = project['allocations'] if include_expired else select_valid_allocations(project['allocations'])
                for allocation in api_allocations:
                    if allocation['resource'] == self.resource_name:
                        user_allocations.append( (project, allocation) )
            return user_allocations
        except ValueError as exc:
            logger.exception('JSON Decode error')
            if raise_exception:
                raise TASAPIException("JSON Decode error -- %s" % exc)
        except Exception:
            logger.exception('Something went wrong while getting user allocations')
            if raise_exception:
                raise
        return None



def get_or_create_allocation_source(api_allocation):
    try:
        source_name = "%s" % (api_allocation['project'],)
        source_id = api_allocation['id']
        compute_allowed = int(api_allocation['computeAllocated'])
    except (TypeError, KeyError, ValueError):
        raise TASAPIException("Malformed API Allocation - Missing keys in dict: %s" % api_allocation)

    payload = {
        'allocation_source_name': source_name,
        'compute_allowed': compute_allowed,
        'start_date':api_allocation['start'],
        'end_date':api_allocation['end']
    }

    try:
        created_event_key = 'sn=%s,si=%s,ev=%s,dc=jetstream,dc=atmosphere' % (
            source_name, source_id, 'allocation_source_created_or_renewed')
        created_event_uuid = uuid.uuid5(uuid.NAMESPACE_X500, str(created_event_key))
        created_event = EventTable.objects.create(name='allocation_source_created_or_renewed',
                                                  uuid=created_event_uuid,
                                                  payload=payload)
        assert isinstance(created_event, EventTable)
    except IntegrityError as e:
        # This is totally fine. No really. This should fail if it already exists and we should ignore it.
        pass

    try:
        compute_event_key = 'ca=%s,sn=%s,si=%s,ev=%s,dc=jetstream,dc=atmosphere' % (
            compute_allowed, source_name, source_id, 'allocation_source_compute_allowed_changed')
        compute_event_uuid = uuid.uuid5(uuid.NAMESPACE_X500, str(compute_event_key))
        compute_allowed_event = EventTable.objects.create(
            name='allocation_source_compute_allowed_changed', uuid=compute_event_uuid, payload=payload)
        assert isinstance(compute_allowed_event, EventTable)
    except IntegrityError as e:
        # This is totally fine. No really. This should fail if it already exists and we should ignore it.
        pass

    source = AllocationSource.objects.get(name__iexact=source_name)
    return source


def find_user_allocation_source_for(driver, user):
    tacc_user = driver.get_tacc_username(user, raise_exception=True)
    # allocations = driver.find_allocations_for(tacc_user)
    project_allocations = driver.get_user_allocations(tacc_user)
    if project_allocations is None:
        return None
    allocations = [pa[1] for pa in project_allocations]  # 2-tuples: (project, allocation)
    return allocations


def fill_allocation_sources():
    driver = TASAPIDriver()
    allocations = driver.get_all_allocations()
    create_list = []
    for api_allocation in allocations:
        obj = get_or_create_allocation_source(api_allocation)
        create_list.append(obj)
    return len(create_list)


def collect_users_without_allocation(driver):
    """
    Should be able to refactor this to make faster...
    """
    from core.models import AtmosphereUser
    missing = []
    for user in AtmosphereUser.objects.order_by('username'):
        tacc_user = driver.get_tacc_username(user)
        if not tacc_user:
            missing.append(user)
            continue
        user_allocations = driver.get_user_allocations(
            tacc_user, raise_exception=False)
        if not user_allocations:
            missing.append(user)
    return missing


def fill_user_allocation_sources():
    from core.models import AtmosphereUser
    driver = TASAPIDriver()
    allocation_resources = {}
    for user in AtmosphereUser.objects.order_by('username'):
        try:
            resources = fill_user_allocation_source_for(driver, user)
        except Exception as exc:
            logger.exception("Error filling user allocation source for %s" % user)
            resources = []
        allocation_resources[user.username] = resources
    return allocation_resources


def fill_user_allocation_source_for(driver, user):
    from core.models import AtmosphereUser
    assert isinstance(user, AtmosphereUser)
    allocation_list = find_user_allocation_source_for(driver, user)
    if allocation_list is None:
        logger.info("find_user_allocation_source_for %s is None, so stop and don't delete allocations" % user.username)
        return
    allocation_resources = []
    user_allocation_sources = []
    old_user_allocation_sources = list(UserAllocationSource.objects.filter(user=user).order_by(
        'allocation_source__name').all())

    for api_allocation in allocation_list:
        allocation_source = get_or_create_allocation_source(api_allocation)
        allocation_resources.append(allocation_source)
        user_allocation_source = get_or_create_user_allocation_source(user, allocation_source)
        user_allocation_sources.append(user_allocation_source)

    canonical_source_names = [source.name for source in allocation_resources]
    for user_allocation_source in old_user_allocation_sources:
        if user_allocation_source.allocation_source.name not in canonical_source_names:
            delete_user_allocation_source(user, user_allocation_source.allocation_source)
    return allocation_resources


def delete_user_allocation_source(user, allocation_source):
    from core.models import AtmosphereUser
    assert isinstance(user, AtmosphereUser)
    assert isinstance(allocation_source, AllocationSource)
    payload = {
        'allocation_source_name': allocation_source.name
    }

    created_event = EventTable.objects.create(name='user_allocation_source_deleted',
                                              entity_id=user.username,
                                              payload=payload)
    assert isinstance(created_event, EventTable)


def get_or_create_user_allocation_source(user, allocation_source):
    from core.models import AtmosphereUser
    assert isinstance(user, AtmosphereUser)
    assert isinstance(allocation_source, AllocationSource)

    user_allocation_source = UserAllocationSource.objects.filter(user=user, allocation_source=allocation_source)

    if not user_allocation_source:
        payload = {
            'allocation_source_name': allocation_source.name
        }

        created_event = EventTable.objects.create(name='user_allocation_source_created',
                                                  entity_id=user.username,
                                                  payload=payload)
        assert isinstance(created_event, EventTable)
        user_allocation_source = UserAllocationSource.objects.get(user=user, allocation_source=allocation_source)
    else:
        user_allocation_source = user_allocation_source.last()

    return user_allocation_source


def select_valid_allocations(allocation_list):
    now = timezone.now()
    allocations = []
    for allocation in allocation_list:
        allocation_status = allocation['status']
        if allocation_status.lower() != 'active':
           #logger.debug("Skipping Allocation %s because its listed status is NOT 'active'" % allocation)
           continue
        start_timestamp = allocation['start']
        end_timestamp = allocation['end']
        start_date = parse(start_timestamp)
        end_date = parse(end_timestamp)
        if start_date >= now or end_date <= now:
           #logger.debug("Skipping Allocation %s because its dates are outside the range for timezone.now()" % allocation)
           continue
        allocations.append(allocation)
    return allocations


def select_valid_allocation(allocation_list):
    """
    #FIXME: In a future commit, merge select_valid_allocations.
    """
    now = timezone.now()
    for allocation in allocation_list:
        status = allocation['status']
        if status.lower() != 'active':
           #logger.info("Skipping Allocation %s because its listed status is NOT 'active'" % allocation)
           continue
        start_timestamp = allocation['start']
        end_timestamp = allocation['end']
        start_date = parse(start_timestamp)
        end_date = parse(end_timestamp)
        if start_date >= now or end_date <= now:
           #logger.info("Skipping Allocation %s because its dates are outside the range for timezone.now()" % allocation)
           continue
        return allocation
    return None


def _validate_tas_data(data):
    if not data or 'status' not in data or 'result' not in data:
        raise TASAPIException(
            "API is returning a malformed response - "
            "Expected json object including "
            "a 'status' key and a 'result' key. - "
            "Received: %s" % data)
    message = data.get('message', '') or ''
    if message.startswith('No account was found with username'):
        raise NoAccountForUsernameException(data)
    if message.startswith('No user found for XSEDE username'):
        raise NoTaccUserForXsedeException(data)
    if data['status'] != 'success':
        raise TASAPIException(
            "API is returning an unexpected status %s - "
            "Received: %s"
            % (data['status'], data)
        )
    return True


