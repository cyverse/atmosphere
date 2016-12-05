# -*- coding: utf-8 -*-
"""
Core views to provide custom operations
"""
import uuid
from datetime import datetime

from django.http import HttpResponseRedirect

from threepio import logger

from atmosphere import settings
from django_cyverse_auth.decorators import atmo_login_required
from django_cyverse_auth.models import Token as AuthToken
from core.models import AtmosphereUser as DjangoUser


@atmo_login_required
def emulate_request(request, username=None):
    try:
        logger.info("Emulate attempt: %s wants to be %s"
                    % (request.user, username))
        logger.info(request.session.__dict__)
        if not username and 'emulator' in request.session:
            logger.info("Clearing emulation attributes from user")
            username = request.session['emulator']
            orig_token = request.session['emulator_token']
            request.session['username'] = username
            request.session['token'] = orig_token
            del request.session['emulator']
            del request.session['emulator_token']
            # Allow user to fall through on line below
            return HttpResponseRedirect(settings.REDIRECT_URL + "/api/v1/profile")

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
        # Keep original emulator+token if it exists, or use the last known username+token
        if 'emulator' not in request.session:
            original_emulator = request.session['username']
            request.session['emulator'] = original_emulator
        if 'emulator_token' not in request.session:
            original_token = request.session['token']
            request.session['emulator_token'] = original_token

        # # Set the username to the user to be emulated
        # # to whom the token also belongs
        request.session['username'] = username
        request.session['token'] = token.key
        request.session.save()
        logger.info("Returning user %s - Emulated as user %s - to api profile "
                    % (original_emulator, username))
        logger.info(request.session.__dict__)
        logger.info(request.user)
        return HttpResponseRedirect(settings.REDIRECT_URL + "/api/v1/profile")
    except Exception as e:
        logger.warn("Emulate request failed")
        logger.exception(e)
        return HttpResponseRedirect(settings.REDIRECT_URL + "/api/v1/profile")
