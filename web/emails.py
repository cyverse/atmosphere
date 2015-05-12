"""
Atmosphere email functions
"""

import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseServerError
from django.template import Context
from django.template.loader import render_to_string

from core.models import AtmosphereUser as User

from threepio import logger

from atmosphere import settings
from core.email import email_admin, email_from_admin
from core.models import IdentityMembership, MachineRequest


def requestImaging(request, machine_request_id, auto_approve=False):
    """
    Processes image request, sends an email to the user
    and a sperate email to atmo@iplantc.org
    Returns a response.
    """
    # TODO: This could also be:
    # machine_request.instance.created_by.username
    # And we could add another field 'new_image_owner'..
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    user = machine_request.new_machine_owner

    subject = 'Atmosphere Imaging Request - %s' % user.username
    context = {
        "user": user,
        "approved": auto_approve,
        "request": machine_request
    }
    body = render_to_string("core/email/imaging_request.html",
                            context=Context(context))
    # Send staff url if not approved
    if not auto_approve:
        namespace = "api:public_apis:cloud-admin-imaging-request-detail"
        base_url = reverse(namespace, args=(machine_request_id,))
        context["view"] = base_url
        context["approve"] = "%s/approve"  % base_url
        context["deny"] = "%s/deny"  % base_url
        staff_body = render_to_string("core/email/imaging_request_staff.html",
                                       context=Context(context))
        email_success = email_admin(request, subject, staff_body,
                                    cc_user=False)

    return email_from_admin(user.username, subject, body)


def quota_request_email(request, username, new_quota, reason):
    """
    Processes Increase Quota request. Sends email to atmo@iplantc.org

    Returns a response.
    """
    user = User.objects.get(username=username)
    membership = IdentityMembership.objects.get(
        identity=user.select_identity(),
        member__in=user.group_set.all())
    admin_url = reverse('admin:core_identitymembership_change',
                                     args=(membership.id,))

    subject = "Atmosphere Quota Request - %s" % username
    context = {
        "user": user,
        "quota": new_quota,
        "reason": reason,
        "url": request.build_absolute_uri(admin_url)
    }
    body = render_to_string("core/email/quota_request.html",
                            context=Context(context))
    logger.info(body)
    email_success = email_admin(request, subject, body, cc_user=False)
    return {"email_sent": email_success}


def feedback_email(request, username, user_email, message):
    """
    Sends an email Bto support based on feedback from a client machine

    Returns a response.
    """
    user = User.objects.get(username=username)
    subject = 'Subject: Atmosphere Client Feedback from %s' % username
    context = {
        "user": user,
        "feedback": message
    }
    body = render_to_string("core/email/feedback.html",
                            context=Context(context))
    email_success = email_admin(request, subject, body, request_tracker=True)
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
    email_success = email_admin(request, subject, message, request_tracker=True)
    return {"email_sent": email_success}
