# -*- coding: utf-8 -*-
"""
Atmosphere core email.
"""
from core.models import AtmosphereUser as User
from core.models import Instance

from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone

from pytz import timezone as pytz_timezone

from django.conf import settings
from core.models import MachineRequest, EmailTemplate

from django_cyverse_auth.protocol.ldap import lookupEmail as ldapLookupEmail, lookupUser
from core.tasks import send_email


def get_email_template():
    """
    Return the one and only EmailTemplate
    so it can be used in (Email templates)! *GASP*
    """
    email_template = EmailTemplate.get_instance()
    return email_template


def send_email_template(
    subject,
    template,
    recipients,
    sender,
    context=None,
    cc=None,
    html=True,
):
    """
    Return task to send an email using the template provided
    """
    body = render_to_string(template, context=context)
    args = (subject, body, sender, recipients)
    kwargs = {"cc": cc, "html": html}
    return send_email.delay(*args, **kwargs)


def email_address_str(name, email):
    """ Create an email address from a name and email.
    """
    return "%s <%s>" % (name, email)


def lookup_user(request):
    """
    Return the username and email given a django request object.
    TODO: Remove this method _OR_ user_email_info
    """
    username = None
    try:
        username = request.session.get('username', '')
    except AttributeError:
        pass
    if not username and hasattr(request, "user"):
        username = request.user.username
    return user_email_info(username)


def djangoLookupEmail(username):
    """
    Use LDAP to query the e-mail, then
    Returns a 3-tuple of:
    ("username", "email@address.com", "My Name")
    """
    try:
        user = User.objects.get(username=username)
        return user.email
    except:
        raise


def django_get_email_info(raw_username):
    """
    Use LDAP to query the e-mail, then
    Returns a 3-tuple of:
    ("username", "email@address.com", "My Name")
    """
    try:
        user = User.objects.get(username=raw_username)
        return (user.username, user.email, user.get_full_name())
    except:
        raise


def ldap_get_email_info(username):
    """
    Use LDAP to query the e-mail, then
    Returns a 3-tuple of:
    ("username", "email@address.com", "My Name")
    """
    try:
        ldap_attrs = lookupUser(username)
    except IndexError:
        raise Exception("Username %s could not be found in LDAP" % username)

    user_email = ldap_attrs.get('mail', [None])[0]
    if not user_email:
        raise Exception(
            "Could not locate email address for User:%s - Attrs: %s" %
            (username, ldap_attrs)
        )
    user_name = ldap_attrs.get('cn', [""])[0]
    if not user_name:
        user_name = "%s %s" % (
            ldap_attrs.get("displayName", [""])[0], ldap_attrs.get("sn",
                                                                   [""])[0]
        )
    if not user_name.strip(' '):
        user_name = username
    return (username, user_email, user_name)


def lookupEmail(username):
    """
    Given a username, return the email address
    """
    if not hasattr(settings, 'EMAIL_LOOKUP_METHOD'):
        return ldapLookupEmail(username)
    lookup_fn = globals()[settings.EMAIL_LOOKUP_METHOD]
    return lookup_fn(username)


def user_email_info(username):
    """
    Returns a 3-tuple of:
    ("username", "email@address.com", "My Name")
    """
    if not hasattr(settings, 'USER_EMAIL_LOOKUP_METHOD'):
        return ldap_get_email_info(username)
    lookup_fn = globals()[settings.USER_EMAIL_LOOKUP_METHOD]
    return lookup_fn(username)


def request_data(request):
    user_agent, remote_ip, location, resolution = request_info(request)
    username, email, name = lookup_user(request)
    return {
        "username": username,
        "email": email,
        "name": name,
        "resolution": resolution,
        "location": location,
        "remote_ip": remote_ip,
        "user_agent": user_agent,
    }


def request_info(request):
    """ Return commonly used information from a django request object.
        user_agent, remote_ip, location, resolution.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    remote_ip = request.META.get('REMOTE_ADDR', '')
    location = request.POST.get('location', 'No Location')
    resolution = 'No Resolution'
    if request.POST.get('resolution[viewport][width]', ''):
        resolution = "viewport( width: " + \
            request.POST.get('resolution[viewport][width]', '') + \
            ", height: " + \
            request.POST.get('resolution[viewport][height]', '') + ") " + \
            "screen( width: " + \
            request.POST.get('resolution[screen][width]', '') + \
            ", height: " + \
            request.POST.get('resolution[screen][height]', '') + ")"
    return (user_agent, remote_ip, location, resolution)


def email_support(subject, body, request):
    """
    Send a basic email to support.
    """
    user, user_email, user_name = lookup_user(request)
    celery_task = send_email.si(
        subject,
        body,
        from_email=email_address_str(user_name, user_email),
        to=[email_address_str(*settings.ATMO_SUPPORT)]
    )
    celery_task.delay()
    return True


def email_admin(subject, body, sender):
    """
    Send a basic email to the admins.
    """
    celery_task = send_email.si(
        subject,
        body,
        from_email=sender,
        to=[email_address_str(name, email) for name, email in settings.ADMINS]
    )
    celery_task.delay()
    return True


def email_from_admin(username, subject, body, html=False):
    """ Use user, subject and body to build and send a standard
        Atmosphere admin email from admins to a user.
        Returns True on success and False on failure.
    """
    sender = email_address_str(*settings.ATMO_DAEMON)
    user_email = lookupEmail(username)
    if not user_email:
        user_email = "%s@%s" % (username, settings.DEFAULT_EMAIL_DOMAIN)
    celery_task = send_email.si(
        subject,
        body,
        from_email=sender,
        to=[email_address_str(username, user_email)],
        cc=[sender],
        html=html
    )
    celery_task.delay()    # Task executes here
    return True


def send_approved_resource_email(user, request, reason):
    """
    Notify the user the that their request has been approved.
    """
    email_template = get_email_template()
    template = "core/email/resource_request_approved.html"
    subject = "Your Resource Request has been approved"
    context = {
        "support_email": email_template.email_address,
        "support_email_header": email_template.email_header,
        "support_email_footer": email_template.email_footer,
        "user": user.username,
        "request": request,
        "reason": reason
    }
    user_email = lookupEmail(user.username)
    recipients = [email_address_str(user.username, user_email)]
    sender = email_address_str(*settings.ATMO_DAEMON)

    return send_email_template(
        subject,
        template,
        recipients,
        sender,
        context=context,
        cc=[sender],
        html=False
    )


def send_denied_resource_email(user, request, reason):
    """
    Send an email notifying the user that their request has been denied.
    """
    email_template = get_email_template()
    template = "core/email/resource_request_denied.html"
    subject = "Your Resource Request has been denied"
    context = {
        "support_email": email_template.email_address,
        "support_email_header": email_template.email_header,
        "support_email_footer": email_template.email_footer,
        "user": user.username,
        "request": request,
        "reason": reason
    }
    user_email = lookupEmail(user.username)
    recipients = [email_address_str(user.username, user_email)]
    sender = email_address_str(*settings.ATMO_DAEMON)

    return send_email_template(
        subject,
        template,
        recipients,
        sender,
        context=context,
        cc=[sender],
        html=False
    )


def send_instance_email(
    username,
    instance_id,
    instance_name,
    ip,
    launched_at,
    linuxusername,
    user_failure=False,
    user_failure_message=""
):
    """
    Sends an email to the user providing information about the new instance.

    Returns a boolean.
    """
    format_string = '%b, %d %Y %H:%M:%S'
    email_template = get_email_template()
    instance = Instance.objects.get(provider_alias=instance_id)
    author = instance.created_by
    provider_location = instance.provider.location
    ssh_keys = [key.name for key in author.sshkey_set.all()]
    username, user_email, user_name = user_email_info(username)
    launched_at = launched_at.replace(tzinfo=None)
    utc_date = django_timezone.make_aware(
        launched_at, timezone=pytz_timezone('UTC')
    )
    local_launched_at = django_timezone.localtime(utc_date)
    getting_started_link = email_template.get_link('getting-started')
    faq_link = email_template.get_link('faq')
    support_email = email_address_str(*settings.ATMO_SUPPORT)
    context = {
        "getting_started_instances_link": getting_started_link.href,
        "getting_started_instances_name": getting_started_link.topic,
        "faq_link": faq_link.href,
        "faq_link_name": faq_link.topic,
        "ssh_keys": ssh_keys,
        "provider_location": provider_location,
        "support_email": support_email,
        "support_email_header": email_template.email_header,
        "support_email_footer": email_template.email_footer,
        "user": user_name,
        "site_name": settings.SITE_NAME,
        "instance_id": instance_id,
        "instance_name": instance_name,
        "instance_ip": ip,
        "sshuser": linuxusername,
        "user_failure": user_failure,
        "user_failure_message": user_failure_message,
        "launched_at": launched_at.strftime(format_string),
        "local_launched_at": local_launched_at.strftime(format_string)
    }
    body = render_to_string("core/email/instance_ready.html", context=context)
    subject = 'Your Atmosphere Instance is Available'
    email_args = (username, subject, body)
    return email_from_admin(*email_args)


def send_allocation_usage_email(
    user,
    allocation_source,
    threshold,
    usage_percentage,
    user_compute_used=None
):
    """
    Sends an email to the user to inform them that their Usage has hit a predefined checkpoint.
    #TODO: Version 2.0 -- The event-sending becomes async (CELERY!)
    #TODO: In version 2.0 we add a 1sec delay before firing this task/listener and allow `allocation_source_snapshot` to be created.
    #TODO: Use the values in `allocation_source_snapshot` and possibly the `TASAPIDriver` to inform the user of more relevant details!
    """
    username, user_email, user_name = user_email_info(user.username)

    # For simplicity, force all values to integer.
    threshold = int(threshold)
    total_used = round(
        float(allocation_source.compute_allowed * (usage_percentage / 100.0)), 2
    )
    usage_percentage = int(usage_percentage)
    if user_compute_used is None:
        user_compute_used = "N/A"
        user_compute_used_percent = "N/A"
    else:
        user_compute_used_percent = int(
            (user_compute_used / allocation_source.compute_allowed) * 100
        )
        user_compute_used = int(user_compute_used)

    allocation_source_total = int(allocation_source.compute_allowed)
    context = {
        "owner": user,
        "user": user_name,
        "email": user_email,
        "allocation_source": allocation_source,
        "allocation_source_total": allocation_source_total,
        "user_compute_used": user_compute_used,
        "user_compute_used_percentage": user_compute_used_percent,
        "threshold": threshold,
        "total_used": total_used,
        "actual": usage_percentage,
    }
    body = render_to_string("core/email/allocation_warning.html", context)
    subject = '(%s) Jetstream Allocation Usage Notice' % username
    return email_from_admin(user.username, subject, body)


def send_preemptive_deploy_failed_email(core_instance, message):
    """
    Sends an email to the admins, who will verify the reason for the error.
    """
    user = core_instance.created_by
    username, user_email, user_name = user_email_info(user.username)
    context = {
        "alias": core_instance.provider_alias,
        "owner": user,
        "user": user_name,
        "email": user_email,
        "ip": core_instance.ip_address,
        "identifier": core_instance.source.providermachine.identifier,
        "details": message
    }
    body = render_to_string("core/email/deploy_warning.html", context)
    subject = '(%s) Preemptive Deploy Failure' % username
    return email_admin(subject, body, email_address_str(user_name, user_email))


def send_deploy_failed_email(core_instance, exception_str):
    """
    Sends an email to the admins, who will verify the reason for the error.
    """
    user = core_instance.created_by
    username, user_email, user_name = user_email_info(user.username)
    context = {
        "alias": core_instance.provider_alias,
        "owner": user,
        "user": user_name,
        "email": user_email,
        "ip": core_instance.ip_address,
        "identifier": core_instance.source.providermachine.identifier,
        "error": exception_str
    }
    body = render_to_string("core/email/deploy_failed.html", context=context)
    subject = '(%s) Deploy Failed' % username
    return email_admin(subject, body, email_address_str(user_name, user_email))


def send_image_request_failed_email(machine_request, exception_str):
    """
    Sends an email to the admins, who will verify the reason for the error,
    with an option to re-approve the request.
    """
    user = machine_request.new_machine_owner
    username, user_email, user_name = user_email_info(user.username)
    approve_link = '%s/api/v1/request_image/%s/approve' \
        % (settings.SERVER_URL, machine_request.id)
    context = {
        "approval_link": approve_link,
        "identifier": machine_request.id,
        "owner": user,
        "user": user_name,
        "email": user_email,
        "alias": machine_request.instance.provider_alias,
        "ip": machine_request.instance.ip_address,
        "error": exception_str
    }
    body = render_to_string("core/email/imaging_failed.html", context=context)
    subject = 'ERROR - Atmosphere Imaging Task has encountered an exception'
    return email_admin(
        subject, body, email_address_str(user.username, user_email)
    )


def send_image_request_email(user, new_machine, name):
    """
    Sends an email to the admins, who will verify the image boots successfully.
    Upon launching, the admins will forward this email to the user,
    which will provide useful information about the new image.
    """
    username, user_email, user_name = user_email_info(user.username)
    email_template = get_email_template()
    context = {
        "user": user_name,
        "identifier": new_machine.identifier,
        "support_email": email_template.email_address,
        "support_email_header": email_template.email_header,
        "support_email_footer": email_template.email_footer,
        "alias": name
    }
    body = render_to_string("core/email/imaging_success.html", context=context)
    subject = 'Your Atmosphere Image is Complete'
    return email_from_admin(user.username, subject, body)


def send_new_provider_email(username, identity):
    if not identity:
        raise Exception("Identity missing -- E-mail will not be sent")
    provider_name = identity.provider.location
    credential_list = identity.credential_set.all()
    email_template = get_email_template()
    subject = (
        "Your %s Atmosphere account has been granted access "
        "to the %s provider" % (settings.SITE_NAME, provider_name)
    )
    context = {
        "new_provider_link": email_template.link_new_provider,
        "support_email": email_template.email_address,
        "support_email_header": email_template.email_header,
        "support_email_footer": email_template.email_footer,
        "user": username,
        "provider": provider_name,
        "credentials": credential_list,
    }
    body = render_to_string("core/email/provider_email.html", context=context)
    return email_from_admin(username, subject, body, html=True)


def requestImaging(request, machine_request_id, auto_approve=False):
    """
    Processes image request, sends an email to the user
    and a sperate email to the admins
    Returns a response.
    """
    # TODO: This could also be:
    # machine_request.instance.created_by.username
    # And we could add another field 'new_image_owner'..
    machine_request = MachineRequest.objects.get(id=machine_request_id)
    user = machine_request.new_machine_owner
    email_template = get_email_template()
    subject = 'Atmosphere Imaging Request - %s' % user.username
    context = {
        "user": user,
        "approved": auto_approve,
        "request": machine_request,
        "support_email": email_template.email_address,
        "support_email_header": email_template.email_header,
        "support_email_footer": email_template.email_footer,
    }
    body = render_to_string("core/email/imaging_request.html", context=context)
    # Send staff url if not approved
    if not auto_approve:
        namespace = "api:v2:machinerequest-detail"
        base_url = reverse(namespace, args=(machine_request_id, ))
        context["view"] = base_url
        context["approve"] = "%s/approve" % base_url
        context["deny"] = "%s/deny" % base_url
        staff_body = render_to_string(
            "core/email/imaging_request_staff.html", context=context
        )
        email_support(subject, staff_body, request)

    return email_from_admin(user.username, subject, body)


def resource_request_email(request, username, quota, reason, options={}):
    """
    Processes Resource request. Sends email to the admins

    Returns a response.
    """

    url = None
    if 'admin_url' in options:
        url = request.build_absolute_uri(options['admin_url'])

    subject = "Atmosphere Resource Request - %s" % username
    context = {"quota": quota, "reason": reason, "url": url}
    context.update(request_data(request))
    body = render_to_string("resource_request.html", context=context)
    success = email_support(subject, body, request)
    return {"email_sent": success}
