import requests

from django.conf import settings
from memoize import memoize

from .exceptions import TASAPIException

from threepio import logger

def tacc_api_post(url, post_data, username=None, password=None):
    if not username:
        username = settings.TACC_API_USER
    if not password:
        password = settings.TACC_API_PASS
    logger.debug('url: %s', url)
    # logger.debug("REQ BODY: %s" % post_data)
    resp = requests.post(
        url, post_data,
        auth=(username, password))
    logger.debug('resp.status_code: %s', resp.status_code)
    # logger.debug('resp.__dict__: %s', resp.__dict__)
    return resp


@memoize(timeout=300)
def tacc_api_get(url, username=None, password=None):
    if not username:
        username = settings.TACC_API_USER
    if not password:
        password = settings.TACC_API_PASS
    logger.debug('url: %s', url)
    resp = requests.get(
        url,
        auth=(username, password))
    logger.debug('resp.status_code: %s', resp.status_code)
    # logger.debug('resp.__dict__: %s', resp.__dict__)
    if resp.status_code != 200:
        raise TASAPIException(
            "Invalid Response - "
            "Expected 200 Response: %s" % resp.__dict__)
    # Expects *ALL* GET calls to return application/json
    try:
        data = resp.json()
        # logger.debug(data)
    except ValueError as exc:
        raise TASAPIException(
            "JSON Decode error -- %s" % exc)
    return (resp, data)
