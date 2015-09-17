# -*- coding: utf-8 -*-
"""
Core views to provide custom operations
"""

import json
import uuid
import os
from datetime import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate as django_authenticate
from django.template import RequestContext
from django.template.loader import get_template

from threepio import logger

from atmosphere import settings
from authentication.decorators import atmo_login_required
from authentication.models import Token as AuthToken
from core.models import AtmosphereUser as DjangoUser
from core.models.instance import Instance



@atmo_login_required
def emulate_request(request, username=None):
    try:
        logger.info("Emulate attempt: %s wants to be %s"
                    % (request.user, username))
        logger.info(request.session.__dict__)
        if not username and 'emulated_by' in request.session:
            logger.info("Clearing emulation attributes from user")
            request.session['username'] = request.session['emulated_by']
            del request.session['emulated_by']
            # Allow user to fall through on line below

        try:
            user = DjangoUser.objects.get(username=username)
        except DjangoUser.DoesNotExist:
            logger.info("Emulate attempt failed. User <%s> does not exist"
                        % username)
            return HttpResponseRedirect(
                settings.REDIRECT_URL +
                "/api/v1/profile")

        logger.info("Emulate success, creating tokens for %s" % username)
        token = AuthToken(
            user=user,
            key=str(uuid.uuid4()),
            issuedTime=datetime.now(),
            remote_ip=request.META['REMOTE_ADDR'],
            api_server_url=settings.API_SERVER_URL
        )
        token.save()
        # Keep original emulator if it exists, or use the last known username
        original_emulator = request.session.get(
            'emulated_by', request.session['username'])
        request.session['emulated_by'] = original_emulator
        # Set the username to the user to be emulated
        # to whom the token also belongs
        request.session['username'] = username
        request.session['token'] = token.key
        logger.info("Returning emulated user - %s - to api profile "
                    % username)
        logger.info(request.session.__dict__)
        logger.info(request.user)
        return HttpResponseRedirect(settings.REDIRECT_URL + "/api/v1/profile")
    except Exception as e:
        logger.warn("Emulate request failed")
        logger.exception(e)
        return HttpResponseRedirect(settings.REDIRECT_URL + "/api/v1/profile")


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


def get_resource(request, file_location):
    try:
        username = request.session.get('username', None)
        remote_ip = request.META.get('REMOTE_ADDR', None)
        if remote_ip is not None:
            # Authenticated if the instance requests resource.
            instances = Instance.objects.filter(ip_address=remote_ip)
            authenticated = len(instances) > 0
        elif username is not None:
            django_authenticate(username=username, password="")
            # User Authenticated by this line
            authenticated = True

        if not authenticated:
            raise Exception("Unauthorized access")
        path = settings.PROJECT_ROOT + "/init_files/" + file_location
        if os.path.exists(path):
            file = open(path, 'r')
            content = file.read()
            response = HttpResponse(content)
            # Download it, even if it looks like text
            response['Content-Disposition'] = \
                'attachment; filename=%s' % file_location.split("/")[-1]
            return response
        template = get_template('404.html')
        variables = RequestContext(request, {
            'message': '%s not found' % (file_location,)
        })
        output = template.render(variables)
        return HttpResponse(output)
    except Exception as e:
        logger.debug("Resource request failed")
        logger.exception(e)
        return HttpResponseRedirect(settings.REDIRECT_URL + "/login")
