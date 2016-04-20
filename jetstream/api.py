import requests

from django.conf import settings

import logging
from .exceptions import TASAPIException
logger = logging.getLogger(__name__)


def tacc_api_post(url, post_data):
    username = settings.TACC_API_USER
    password = settings.TACC_API_PASS
    logger.info(url)
    logger.info(post_data)
    resp = requests.post(
        url, post_data,
        auth=(username, password))
    logger.info(resp.__dict__)
    return resp


def tacc_api_get(url):
    username = settings.TACC_API_USER
    password = settings.TACC_API_PASS
    logger.info(url)
    resp = requests.get(
        url,
        auth=(username, password))
    logger.info(resp.__dict__)
    if resp.status_code != 200:
        raise TASAPIException(
            "Invalid Response - "
            "Expected 200 Response: %s" % resp)
    # Expects *ALL* GET calls to return application/json
    try:
        data = resp.json()
    except ValueError as exc:
        raise TASAPIException(
            "JSON Decode error -- %s" % exc)
    return (resp, data)
