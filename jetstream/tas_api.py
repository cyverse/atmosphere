import requests

from django.conf import settings

import logging
from .exceptions import TASAPIException
logger = logging.getLogger(__name__)


def tacc_api_post(url, post_data, username=None, password=None):
    if not username:
        username = settings.TACC_API_USER
    if not password:
        password = settings.TACC_API_PASS
    logger.info("REQ: %s" % url)
    logger.info("REQ BODY: %s" % post_data)
    resp = requests.post(
        url, post_data,
        auth=(username, password))
    logger.info("RESP: %s" % resp.__dict__)
    return resp


def tacc_api_get(url, username=None, password=None):
    if not username:
        username = settings.TACC_API_USER
    if not password:
        password = settings.TACC_API_PASS
    logger.info("REQ: %s" % url)
    resp = requests.get(
        url,
        auth=(username, password))
    logger.info("RESP: %s" % resp.__dict__)
    if resp.status_code != 200:
        raise TASAPIException(
            "Invalid Response - "
            "Expected 200 Response: %s" % resp.__dict__)
    # Expects *ALL* GET calls to return application/json
    try:
        data = resp.json()
        #logger.info(data)
    except ValueError as exc:
        raise TASAPIException(
            "JSON Decode error -- %s" % exc)
    return (resp, data)
