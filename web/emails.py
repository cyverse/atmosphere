"""
Atmosphere email functions
"""

import json

from django.http import HttpResponse, HttpResponseServerError

from atmosphere.logger import logger
from core.email import email_admin, user_address


def requestImaging(request, approve_link, deny_link):
    """
    Processes image request, sends an email to atmo@iplantc.org
    Returns a response.
    """
    name = request.POST.get('name', '')
    instance_id = request.POST.get('instance', '')
    description = request.POST.get('description', '')
    software = request.POST.get('installed_software', '')
    sys_files = request.POST.get('sys',  '')
    tags = request.POST.get('tags', '')
    public = request.POST.get('vis', '')
    shared_with = request.POST.get('shared_with', '')
    username = request.POST.get('owner', '')
    message = """
    Approve Request: %s
    Deny Request: %s
    ---
    Username : %s
    Instance ID:%s
    ---
    Installed software:%s
    System Files changed:%s
    Image visiblity:%s
    Shared with (Private only):%s
    ---
    New Image name:%s
    New Image description:%s
    New Image tags:%s
    """ % (approve_link, deny_link, username, instance_id, software,
           sys_files, public, shared_with, name, description, tags)
    subject = 'Atmosphere Imaging Request - %s' % username
    email_success = email_admin(request, subject, message)
    json.dumps({})
    return email_success


def requestQuota(request):
    """
    Processes Increase Quota request. Sends email to atmo@iplantc.org

    Returns a response.
    """
    username = request.POST['username']
    new_quota = request.POST['quota']
    reason = request.POST['reason']
    message = """
    Username : %s
    Quota Requested: %s
    Reason for Quota Increase: %s
    """ % (username, new_quota, reason)
    subject = "Atmosphere Quota Request - %s" % username
    logger.info(message)
    email_success = email_admin(request, subject, message)
    resp = json.dumps({})
    if email_success:
        return HttpResponse(resp, content_type='application/json')
    else:
        return HttpResponseServerError(resp, content_type='application/json')


def feedback(request):
    """
    Sends an email Bto support based on feedback from a client machine

    Returns a response.
    """
    user, user_email = user_address(request)
    message = request.POST.get('message')
    subject = 'Subject: Atmosphere Client Feedback from %s' % user
    message = '---\nFeedback: %s\n---' % message
    email_success = email_admin(request, subject, message)
    if email_success:
        resp = json.dumps({'result':
                           {'code': 'success',
                            'meta': '',
                            'value': 'Thank you for your feedback! '
                                     + 'Support has been notified.'}})
        return HttpResponse(resp,
                            content_type='application/json')
    else:
        resp = json.dumps({'result':
                           {'code': 'failed',
                            'meta': '',
                            'value': 'Failed to send feedback!'}})
        return HttpResponse(resp,
                            content_type='application/json')


def email_support(request):
    """
    Sends an email to support.

    POST Params expected:
      * user
      * message
      * subject

    Returns a response.
    """
    message = request.POST.get('message')
    subject = request.POST.get('subject')
    email_success = email_admin(request, subject, message)
    resp = json.dumps({'email_sent': email_success})
    if email_success:
        return HttpResponse(resp,
                            content_type='application/json')
    else:
        return HttpResponseServerError(resp,
                                       content_type='application/json')
