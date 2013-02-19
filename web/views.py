"""
Atmosphere web views.

"""

import os
import json
import ldap
import uuid
import urllib
import urllib2
import httplib2
from datetime import datetime

# django http libraries
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate as django_authenticate, login as django_login
from django.contrib.auth.models import User as DjangoUser

#Added, missing for some reason
from django.shortcuts import render_to_response
from django.template import RequestContext

# django template library
from django.template import Context, TemplateDoesNotExist
from django.template.loader import get_template

import caslib

# atmosphere libraries
from atmosphere import settings
from atmosphere.logger import logger

from auth import cas_loginRedirect, cas_logoutRedirect
from auth.models import Token as AuthToken
from auth.decorators import atmo_login_required, atmo_valid_token_required

from core.models.euca_key import Euca_Key
from core.models.maintenance import MaintenanceRecord
from core.models.instance import Instance
from core.email import email_admin, email_from_admin, user_address

def no_user_redirect(request):
    """
    Shows a screen similar to login with information on how to create an atmosphere account
    """
    template = get_template('application/no_user.html')
    variables = RequestContext(request, {})
    output = template.render(variables)
    return HttpResponse(output)

def redirectApp(request) :
    """
    Redirects to /application if user is authorized, otherwise forces a login
    """
    newURL = (settings.REDIRECT_URL+'/application/') if request.session.get('username') else (settings.REDIRECT_URL+'/login/')
    logger.info('Sending user to:%s' % newURL)
    return HttpResponseRedirect(newURL)

def login(request):
    """
     CAS Login : Phase 1/3 Call CAS Login
    """
    #logger.info("Login Request:%s" % request)
    #Form Sets 'next' when user clicks login
    records = MaintenanceRecord.active()
    disable_login = False
    for record in records:
        if record.disable_login:
            disable_login = True

    if 'next' in request.POST:
        return cas_loginRedirect(request,settings.REDIRECT_URL+'/application/')
    else:
        template = get_template('application/login.html')
        
        variables = RequestContext(request, {
                'site_root': settings.REDIRECT_URL,
                'records': [r.json() for r in records],
                'disable_login' : disable_login
                })
        output = template.render(variables)
        return HttpResponse(output)

def cas_validateTicket(request):
    """
      Phase 2/3 Call CAS serviceValidate
      Phase 3/3 - Return result and original request
    """
    ticket = request.META['HTTP_X_AUTH_TICKET'] if 'HTTP_X_AUTH_TICKET' in request.META else None
    (result,username) = caslib.cas_serviceValidate(ticket)
    if(result == True):
        logging.info("Username for CAS Ticket= "+username)
    if 'HTTP_X_AUTH_USER' in request.META:
        checkUser = request.META['HTTP_X_AUTH_USER']
        logging.info("Existing user found in header, checking for match")
        if checkUser != username:
            logging.info("Existing user doesn't match new user, start new session")
            return (False,None)
        request.META['HTTP_X_AUTH_USER'] = username
    return (result,request)

def logout(request) :
    if request.session.has_key('emulated_by'):
        del request.session['emulated_by']
    if request.session.has_key('username'):
        del request.session['username']
    if request.session.has_key('token'):
        del request.session['token']
    if request.session.has_key('api_server'):
        del request.session['api_server']
    return cas_logoutRedirect()

@atmo_login_required
def app(request):
    try:
        if MaintenanceRecord.disable_login_access():
            return HttpResponseRedirect('/login/')
        template = get_template("cf2/index.html")
        context = RequestContext(request, {
        'site_root': settings.REDIRECT_URL,
            'debug': settings.DEBUG,
            'year': datetime.now().year
        })
        output = template.render(context)
        return HttpResponse(output)
    except KeyError, e:
        logger.debug("User not logged in.. Redirecting to CAS login")
        return cas_loginRedirect(request, settings.REDIRECT_URL+'/application')
    except Exception, e:
        logger.exception(e)
        return cas_loginRedirect(request, settings.REDIRECT_URL+'/application')

@atmo_valid_token_required
def partial(request, path, return_string=False):
    logger.debug("Partial request")

    if path == 'init_data.js':
        logger.info("init_data.js has yet to be implemented with the new service")
    elif path == 'templates.js':
        output = compile_templates()

    response = HttpResponse(output, 'text/javascript')
    response['Cache-Control'] = 'no-cache'
    response['Expires'] = '-1'
    return response

def compile_templates():
    """
    Compiles backbonejs app into a single js file. Returns string.
    Pulled out into its own function so it can be called externally to
    compile production-ready js
    """
    template = get_template("cf2/partials/cloudfront2.js")
    context_dict = {
        'site_root': settings.SERVER_URL,
        'templates': {},
        'files': {}
    }
    js_files_path = os.path.join(settings.root_dir, 'resources', 'js', 'cf2', 'templates')

    for root, dirs, files in os.walk(js_files_path):
        if files:
    #         logger.debug(sorted(files))
             for f in sorted(files):
                 fullpath = os.path.join(root, f)
                 name, ext = os.path.splitext(f)
                 #         #logger.debug(name)
                 #         #logger.debug(ext)
                 file = open(fullpath, 'r')
                 output = file.read()
    #             if ext == '.js' and not '#' in name:
    #                 context_dict['files'][os.path.relpath(fullpath, js_files_path)] = output
                 if ext == '.html':
                     context_dict['templates'][name] = output
                    
    context = Context(context_dict)
    output = template.render(context)
    return output

@atmo_valid_token_required
def instance_graph(request, instance_id=None, metric=None):
    h = httplib2.Http()
    if metric is not None:
        url = "http://dedalus.iplantcollaborative.org/instances/graph_data/%s/%s" % (instance_id, metric)
        params = {}
    else:
        url = "http://dedalus.iplantcollaborative.org/instances/instance_data"
        params = {"euca_id": request.GET.get('instance_id')}
        if request.GET.__contains__('start'):
            params['start'] = request.GET.get('start')
    resp, content = h.request(url + "?" + urllib.urlencode(params), "GET")
    logger.debug('request against %s returned reponse %s' % (url, resp))
    response = HttpResponse(content, content_type='application/json', status=int(resp['status']));
    return response

@atmo_login_required
def application(request) :
    try :
        logger.debug("APPLICATION")
        logger.debug(str(request.session.__dict__))
        access_log(request,meta_data = "{'userid' : '%s', 'token' : '%s', 'api_server' : '%s'}" %(request.session['username'], request.session['token'],request.session['api_server']))
        template = get_template('application/application.html')
    except Exception, e:
        logger.exception(e)
        return HttpResponseRedirect(settings.REDIRECT_URL+'/login')

    variables = RequestContext(request, {})
    output = template.render(variables)
    return HttpResponse(output)
    #return render_to_response(template, {}, context_instance=RequestContext(request))

@atmo_login_required
def emulate_request(request,username=None):
    try:
        logger.info("Emulate attempt: %s wants to be %s" % (request.user,username))
        logger.info(request.session.__dict__)
        if not username and request.session.has_key('emulated_by'):
            logger.info("Clearing emulation attributes from user")
            request.session['username'] = request.session['emulated_by']
            del request.session['emulated_by']
            #Allow user to fall through on line below

        try:
            user= DjangoUser.objects.get(username=username)
        except DjangoUser.DoesNotExist, dne:
            logger.info("Emulate attempt failed. User <%s> does not exist" % username)
            return HttpResponseRedirect(settings.REDIRECT_URL+"/application")

        logger.info("Emulate success, creating tokens for %s" % username)
        token = AuthToken(
            user=user,
            key=str(uuid.uuid4()),
            issuedTime = datetime.now(),
            remote_ip=request.META['REMOTE_ADDR'],
            api_server_url = settings.API_SERVER_URL
        )
        token.save()
        #Keep original emulator if it exists, or use the last known username
        original_emulator = request.session.get('emulated_by',request.session['username'])
        request.session['emulated_by'] = original_emulator
        #Set the username to the user to be emulated, to whom the token also belongs
        request.session['username'] = username
        request.session['token'] = token.key
        logger.info("Returning emulated user - %s - to application " % username)
        logger.info(request.session.__dict__)
        logger.info(request.user)
        return HttpResponseRedirect(settings.REDIRECT_URL+"/application/")
    except Exception, e:
        logger.warn("Emulate request failed")
        logger.warn("%s %s %s" % (e, str(e), e.message))
        return HttpResponseRedirect(settings.REDIRECT_URL+"/application/")

def ip_request(req):
    """
    Used so that an instance can query information about itself
    Valid only if REMOTE_ADDR refers to a valid instance
    """
    logger.debug(req)
    status = 500
    try:
        instances = []
        if req.META.has_key('REMOTE_ADDR'):
            logging.debug("Using request IP")
            testIP = req.META['REMOTE_ADDR']
            instances = Instance.objects.filter(ip_address=testIP)
        if settings.DEBUG:
            if req.GET.has_key('instanceid'):
                instance_id = req.GET['instanceid']
                instances = Instance.objects.filter(provider_alias=instance_id)

        if len(instances) > 0:
            instance = instances[0]
            json = json.dumps({'result':
                               {'code': 'success',
                                'meta': '',
                                'value': 'Thank you for your feedback! Support has been notified.'}})
            status = 200
        else:
            json = json.dumps({'result':
                               {'code': 'failed',
                                'meta': '',
                                'value': 'No instance found with requested IP address'}})
            status = 404
    except Exception, e:
        logger.debug("IP request failed")
        logger.debug("%s %s %s" % (e, str(e), e.message))
        json = json.dumps({'result':
                           {'code': 'failed',
                            'meta': '',
                            'value': 'An error occured'}})
        status = 500
    response = HttpResponse(json, status=status, content_type='application/json')
    return response

def get_resource(request, file_location):
    try:
        username = request.session.get('username',None)
        remote_ip = request.META.get('REMOTE_ADDR',None)
        if remote_ip is not None:
            #Authenticated if the instance requests resource.
            instances = Instance.objects.filter(public_dns_name = remote_ip)
            authenticated = len(instances) > 0
        elif username is not None:
            user = django_authenticate(username=username, password="")
            #User Authenticated by this line
            authenticated = True

        if not authenticated:
            raise Exception("Unauthorized access")
        path = settings.PROJECT_ROOT+"/init_files/"+file_location
        if os.path.exists(path):
            file = open(path,'r')
            content = file.read()
            response = HttpResponse(content)
            #Download it, even if it looks like text
            response['Content-Disposition'] = 'attachment; filename=%s' % file_location.split("/")[-1]
            return response
        template = get_template('404.html')
        variables = RequestContext(request, {
            'message': '%s not found' % (file_location,)
        })
        output = template.render(variables)
        return HttpResponse(output)
    except Exception, e:
        logger.debug("Resource request failed")
        logger.exception(e)
        return HttpResponseRedirect(settings.REDIRECT_URL+"/login")

# @atmo_login_required
# def logs(request):
#     from service_old.models import Log_Message
#     logger.debug(request.user)
#     logger.debug(request.user.is_staff)
#     if not request.user.is_staff:
#         return HttpResponseForbidden('403: Forbidden')

#     if request.GET.has_key('id_lt'):
#         messages = Log_Message.objects.filter(path_name__startswith=settings.PROJECT_ROOT,id__lt=request.GET['id_lt']).order_by('-id')[0:100]
#     elif request.GET.has_key('id_gt'):
#         messages = Log_Message.objects.filter(path_name__startswith=settings.PROJECT_ROOT,id__gt=request.GET['id_gt']).order_by('-id')[0:100]
#     else:
#         messages = Log_Message.objects.filter(path_name__startswith=settings.PROJECT_ROOT).order_by('-id')[0:100]

#     for message in messages:
#         message.created_unix = int(message.created.strftime('%s'))

#     format = 'json'
#     if request.META.has_key('HTTP_ACCEPT'):
#         accept_str = request.META['HTTP_ACCEPT']
#         htmlpos = accept_str.find('text/html')
#         jsonpos = accept_str.find('application/json')
#         if ((htmlpos >= 0 and jsonpos >= 0) and (htmlpos < jsonpos)) or (htmlpos >=0 and jsonpos == -1):
#             format = 'html'

#     if format == 'html':
#         template = get_template("admin/logs.html")

#         context_dict = {
#           'site_root': settings.SERVER_URL,
#           'messages': messages,
#           'username': request.session.get('username')
#         }

#         context = RequestContext(request, context_dict)
#         output = template.render(context)
#         return HttpResponse(output)
#     else:
#         message_arr = [];
#         for message in messages:
#             message_arr.append({
#               'id': message.id,
#               'logger': message.logger,
#               'level_name': message.level_name,
#               'level_no': message.level_no,
#               'path_name': message.path_name,
#               'line_no': message.line_no,
#               'message': message.message,
#               'created': message.created_unix
#             })

#         output = json.dumps(message_arr)
#         response = HttpResponse(output)
#         response['Content-Type'] = 'application/json'
#         response['Cache-Control'] = 'no-cache'
#         return response

