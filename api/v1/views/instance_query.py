# -*- coding: utf-8 -*-
"""
Instance query endpoint
"""
import json

from django.http import HttpResponse

from threepio import logger

from atmosphere import settings
from core.models.instance import Instance


def ip_request(req):
    """
    Used so that an instance can query information about itself
    Valid only if REMOTE_ADDR refers to a valid instance
    """
    logger.debug(req)
    status = 500
    try:
        instances = []
        if 'REMOTE_ADDR' in req.META:
            testIP = req.META['REMOTE_ADDR']
            instances = Instance.objects.filter(ip_address=testIP)
        if settings.DEBUG:
            if 'instanceid' in req.GET:
                instance_id = req.GET['instanceid']
                instances = Instance.objects.filter(provider_alias=instance_id)

        if len(instances) > 0:
            _json = json.dumps({'result':
                                {'code': 'success',
                                 'meta': '',
                                 'value': ('Thank you for your feedback!'
                                           'Support has been notified.')}})
            status = 200
        else:
            _json = json.dumps({'result':
                                {'code': 'failed',
                                 'meta': '',
                                 'value': ('No instance found '
                                           'with requested IP address')}})
            status = 404
    except Exception as e:
        logger.debug("IP request failed")
        logger.debug("%s %s %s" % (e, str(e), e.message))
        _json = json.dumps({'result':
                            {'code': 'failed',
                             'meta': '',
                             'value': 'An error occured'}})
        status = 500
    response = HttpResponse(_json,
                            status=status, content_type='application/json')
    return response
