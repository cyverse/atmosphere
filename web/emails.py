"""
Atmosphere email functions
"""

import json

from django.http import HttpResponse, HttpResponseServerError

from core.models import AtmosphereUser as User
from django.core import urlresolvers

from threepio import logger

from atmosphere import settings
from core.email import email_admin, email_from_admin, user_address
from core.models import IdentityMembership, MachineRequest


def requestImaging(request, machine_request_id):
    """
    Processes image request, sends an email to the user
    and a sperate email to atmo@iplantc.org
    Returns a response.
    """
    view_link = '%s/api/v1/request_image/%s' \
        % (settings.SERVER_URL, machine_request_id)
    approve_link = '%s/api/v1/request_image/%s/approve' \
        % (settings.SERVER_URL, machine_request_id)
    deny_link = '%s/api/v1/request_image/%s/deny' \
        % (settings.SERVER_URL, machine_request_id)
    staff_header = """
    URLs require staff access to view/approve/deny:
    View Request: %s
    Auto-Approve Request: %s
    Auto-Deny Request: %s
    ---
    """ % (view_link, approve_link, deny_link)
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    #TODO: This could also be:
    #machine_request.instance.created_by.username
    #And we could add another field 'new_image_owner'..
    username = machine_request.new_machine_owner.username
    message = """
    Your Image Request has been received.
    Upon staff approval, another e-mail will be sent,
    followed by a final e-mail when the imaging process is complete.

    Your Image Request:
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
    """ % (username, 
           machine_request.instance.provider_alias,
           machine_request.installed_software,
           machine_request.iplant_sys_files,
           machine_request.new_machine_visibility,
           machine_request.access_list,
           machine_request.new_machine_name,
           machine_request.new_machine_description,
           machine_request.new_machine_tags)
    subject = 'Atmosphere Imaging Request - %s' % username
    email_success = email_from_admin(username, subject, message)
    message = "%s\n%s" % (staff_header, message)
    email_success = email_admin(request, subject, message, cc_user=False)
    return email_success


def quota_request_email(request, username, new_quota, reason):
    """
    Processes Increase Quota request. Sends email to atmo@iplantc.org

    Returns a response.
    """
    user = User.objects.get(username=username)
    membership = IdentityMembership.objects.get(identity=user.select_identity(),
            member__in=user.group_set.all())
    admin_url = urlresolvers.reverse('admin:core_identitymembership_change',
                                     args=(membership.id,))
    message = """
    Username : %s
    Quota Requested: %s
    Reason for Quota Increase: %s
    URL for Quota Increase:%s
    """ % (username, new_quota, reason, 
           request.build_absolute_uri(admin_url))
    subject = "Atmosphere Quota Request - %s" % username
    logger.info(message)
    email_success = email_admin(request, subject, message, cc_user=False)
    return {"email_sent": email_success}


def feedback_email(request, username, user_email, message):
    """
    Sends an email Bto support based on feedback from a client machine

    Returns a response.
    """
    subject = 'Subject: Atmosphere Client Feedback from %s' % username
    message = '---\nFeedback: %s\n---' % message
    email_success = email_admin(request, subject, message)
    if email_success:
        resp = {'result':
                   {'code': 'success',
                    'meta': '',
                    'value': 'Thank you for your feedback! '
                             + 'Support has been notified.'}}
    else:
        resp = {'result':
                {'code': 'failed',
                 'meta': '',
                 'value': 'Failed to send feedback!'}}
    return resp


def support_email(request, subject, message):
    """
    Sends an email to support.

    POST Params expected:
      * user
      * message
      * subject

    Returns a response.
    """
    email_success = email_admin(request, subject, message)
    return {"email_sent": email_success}
