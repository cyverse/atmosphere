# -*- coding: utf-8 -*-
"""
Core views to provide custom operations
"""
import uuid
from datetime import datetime

from django.http import HttpResponseRedirect

from threepio import logger

from atmosphere import settings
from iplantauth.decorators import atmo_login_required
from iplantauth.models import Token as AuthToken
from core.models import AtmosphereUser as DjangoUser


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
