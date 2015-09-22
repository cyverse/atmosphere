# -*- coding: utf-8 -*-
"""
Get file resources
"""
import os

from django.contrib.auth import authenticate
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.template.loader import get_template

from threepio import logger

from atmosphere import settings
from core.models.instance import Instance


def get_resource(request, file_location):
    try:
        username = request.session.get('username', None)
        remote_ip = request.META.get('REMOTE_ADDR', None)
        if remote_ip is not None:
            # Authenticated if the instance requests resource.
            instances = Instance.objects.filter(ip_address=remote_ip)
            authenticated = len(instances) > 0
        elif username is not None:
            authenticate(username=username, password="")
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
