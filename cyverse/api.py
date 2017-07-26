import requests

from threepio import logger
from django.conf import settings


def grouper_api_get(path, query_params=None, search_user=None):
    url = settings.GROUPER_API + path
    if not search_user:
        search_user = settings.GROUPER_SEARCH_USER
    if not query_params:
        query_params = "?user=%s" % search_user
    else:
        query_params += "&user=%s" % search_user
    url += query_params
    logger.info("REQ: %s" % url)
    resp = requests.get(
        url,
        headers={"Accept": "application/json"})
    if resp.status_code != 200:
        raise Exception(
            "Invalid Response - "
            "Expected 200 Response: %s" % resp.__dict__)
    try:
        data = resp.json()
    except ValueError as exc:
        raise Exception(
            "JSON Decode error -- %s" % exc)
    return (resp, data)


class GrouperDriver(object):
    search_user = None
    group_list = []
    username_map = {}

    def __init__(self, search_user=None):
        if not search_user:
            search_user = settings.GROUPER_SEARCH_USER
        self.search_user = search_user

    def clear_cache(self):
        self.user_project_list = []
        self.project_list = []
        self.allocation_list = []
        self.username_map = {}

    def get_groups_for_username(self, username):
        path = '/subjects/%s/groups' % username
        resp, data = grouper_api_get(path)
        groups = data['groups']
        return groups

    def get_user(self, username):
        path = '/subjects/%s' % username
        resp, user = grouper_api_get(path)
        return user

    def get_group_privileges(self, groupname):
        path = "/groups/%s/privileges" % groupname
        resp, data = grouper_api_get(path)
        privileges = data['privileges']
        return privileges

    def get_group_leaders(self, groupname):
        privileges = self.get_group_privileges(groupname)
        leaders = []
        for privilege in privileges:
            if privilege['name'] != 'admin':
                logger.info("Skip privilege %s" % privilege['name'])
            leader = privilege['subject']
            leaders.append(leader['id'])
        return leaders

    def is_leader(self, groupname, username):
        leaders = self.get_group_leaders(groupname)
        return username in leaders
