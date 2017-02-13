# -*- coding: utf-8 -*-
"""
Atmosphere core email.
"""
from core.models import AtmosphereUser as User
from core.models import Instance

from django.core.urlresolvers import reverse
from django.db.models import ObjectDoesNotExist
from django.template import Context
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone

from pytz import timezone as pytz_timezone

from threepio import logger

from atmosphere import settings
from core.models.allocation_source import total_usage
from core.models import IdentityMembership, MachineRequest, EmailTemplate

from django_cyverse_auth.protocol.ldap import lookupEmail as ldapLookupEmail, lookupUser
from core.tasks import send_email


def get_email_template():
    """
    Return the one and only EmailTemplate
    so it can be used in (Email templates)! *GASP*
    """
    email_template = EmailTemplate.get_instance()
    return email_template

def send_email_template(subject, template, recipients, sender,
                        context=None, cc=None, html=True, silent=False):
    """
    Return task to send an email using the template provided
    """
    body = render_to_string(template, context=Context(context))
    args = (subject, body, sender, recipients)
    kwargs = {
        "cc": cc,
        "fail_silently": silent,
        "html": html
    }
    return send_email.si(*args, **kwargs)


def email_address_str(name, email):
    """ Create an email address from a name and email.
    """
    return "%s <%s>" % (name, email)


def request_tracker_address():
    """ Return the admin name and admin email from
        django's settings.
    """
    return (settings.ATMO_SUPPORT[0][0], settings.ATMO_SUPPORT[0][1])


def admin_address(test_user=None):
    """ Return the admin name and admin email from
        django's settings.
    """
    if test_user:
        for admin_user, admin_email in settings.ADMINS:
            if admin_user == test_user:
                return admin_user, admin_email
    return (settings.ADMINS[0][0], settings.ADMINS[0][1])


def atmo_daemon_address():
    """ Return the daemon email address.
    """
    return (settings.ATMO_DAEMON[0][0], settings.ATMO_DAEMON[0][1])


def lookup_user(request):
    """
    Return the username and email given a django request object.
    TODO: Remove this method _OR_ user_email_info
    """
    try:
        username = request.session.get('username', '')
    except:
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
    (username, user_email, user_name) = ("", "", "")
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
            (username, ldap_attrs))
    user_name = ldap_attrs.get('cn', [""])[0]
    if not user_name:
        user_name = "%s %s" % (ldap_attrs.get("displayName", [""])[0],
                               ldap_attrs.get("sn", [""])[0])
    if not user_name.strip(' '):
        user_name = username
    return (username, user_email, user_name)




def lookupEmail(username):
    """
    Given a username, return the email address
    """
    if not hasattr(settings, 'EMAIL_LOOKUP_METHOD'):
        return ldapLookupEmail(username)
    lookup_fn_str = settings.EMAIL_LOOKUP_METHOD
    lookup_fn = settings._get_method_for_string(lookup_fn_str, the_globals=globals())
    # Known function and args..
    return lookup_fn(username)

def user_email_info(username):
    """
    Returns a 3-tuple of:
    ("username", "email@address.com", "My Name")
    """
    if not hasattr(settings, 'USER_EMAIL_LOOKUP_METHOD'):
        return ldap_get_email_info(username)
    lookup_fn_str = settings.USER_EMAIL_LOOKUP_METHOD
    lookup_fn = settings._get_method_for_string(lookup_fn_str, the_globals=globals())
    # Known function and args..
    return lookup_fn(username)


def request_data(request):
    user_agent, remote_ip, location, resolution = request_info(request)
    username, email, name = lookup_user(request)
    return {
        "username" : username,
        "email" : email,
        "name" : name,
        "resolution" : resolution,
        "location" : location,
        "remote_ip" : remote_ip,
        "user_agent" : user_agent,
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

def email_admin(request, subject, message,
        cc_user=True, request_tracker=False, html=False):
    """ Use request, subject and message to build and send a standard
        Atmosphere user request email. From an atmosphere user to admins.
        Returns True on success and False on failure.
    """
    user_agent, remote_ip, location, resolution = request_info(request)
    user, user_email, user_name = lookup_user(request)
    return email_to_admin(subject, message, user, user_email, cc_user=cc_user,
                          request_tracker=request_tracker, html=html)


def email_to_admin(
        subject,
        body,
        username=None,
        user_email=None,
        cc_user=True,
        admin_user=None,
        request_tracker=False,
        html=False):
    """
    Send a basic email to the admins. Nothing more than subject and message
    are required.
    """
    if admin_user:
        sendto, sendto_email = admin_address(admin_user)
    elif request_tracker:
        sendto, sendto_email = request_tracker_address()
    else:
        sendto, sendto_email = admin_address()
    # E-mail yourself if no users are provided
    if not username and not user_email:
        username, user_email = sendto, sendto_email
    elif not user_email:  # Username provided
        # TODO: Pass only strings, avoid passing 'User' object here.
        if isinstance(username, User):
            username = username.username
        user_email = lookupEmail(username)
        if not user_email:
            user_email = "%s@%s" % (username, settings.DEFAULT_EMAIL_DOMAIN)
    elif not username:  # user_email provided
        username = 'Unknown'
    if request_tracker or not cc_user:
        # Send w/o the CC
        cc = []
    else:
        cc = [email_address_str(username, user_email)]
    celery_task = send_email.si(subject, body,
               from_email=email_address_str(username, user_email),
               to=[email_address_str(sendto, sendto_email)],
               cc=cc,
               html=html)
    celery_task.delay() # Task executes here
    return True


def email_from_admin(username, subject, message, html=False):
    """ Use user, subject and message to build and send a standard
        Atmosphere admin email from admins to a user.
        Returns True on success and False on failure.
    """
    from_name, from_email = admin_address()
    user_email = lookupEmail(username)
    if not user_email:
        user_email = "%s@%s" % (username, settings.DEFAULT_EMAIL_DOMAIN)
    celery_task = send_email.si(subject, message,
               from_email=email_address_str(from_name, from_email),
               to=[email_address_str(username, user_email)],
               cc=[email_address_str(from_name, from_email)],
               html=html)
    celery_task.delay() # Task executes here
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
    from_name, from_email = admin_address()
    user_email = lookupEmail(user.username)
    recipients = [email_address_str(user.username, user_email)]
    sender = email_address_str(from_name, from_email)

    return send_email_template(subject, template, recipients, sender,
                               context=context, cc=[sender])


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
    from_name, from_email = admin_address()
    user_email = lookupEmail(user.username)
    recipients = [email_address_str(user.username, user_email)]
    sender = email_address_str(from_name, from_email)

    return send_email_template(subject, template, recipients, sender,
                               context=context, cc=[sender])


def send_instance_email(username, instance_id, instance_name,
                        ip, launched_at, linuxusername, user_failure=False, user_failure_message=""):
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
    utc_date = django_timezone.make_aware(launched_at,
                                          timezone=pytz_timezone('UTC'))
    local_launched_at = django_timezone.localtime(utc_date)
    getting_started_link = email_template.get_link('getting-started')
    faq_link = email_template.get_link('faq')
    support_email = settings.SUPPORT_EMAIL
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
    body = render_to_string(
        "core/email/instance_ready.html",
        context=Context(context))
    subject = 'Your Atmosphere Instance is Available'
    email_args = (username, subject, body)
    return email_from_admin(*email_args)


def send_allocation_usage_email(user, allocation_source, threshold, usage_percentage, user_compute_used=None):
    """
    Sends an email to the user to inform them that their Usage has hit a predefined checkpoint.
    #TODO: Version 2.0 -- The event-sending becomes async (CELERY!)
    #TODO: In version 2.0 we add a 1sec delay before firing this task/listener and allow `allocation_source_snapshot` to be created.
    #TODO: Use the values in `allocation_source_snapshot` and possibly the `TASAPIDriver` to inform the user of more relevant details!
    """
    username, user_email, user_name = user_email_info(user.username)

    # For simplicity, force all values to integer.
    usage_percentage = int(usage_percentage)
    threshold = int(threshold)
    total_used = int(allocation_source.compute_allowed * (usage_percentage/100.0))
    if user_compute_used is None:
        user_compute_used = "N/A"
        user_compute_used_percent = "N/A"
    else:
        user_compute_used_percent = int((user_compute_used/allocation_source.compute_allowed)*100)
        user_compute_used = min(int(user_compute_used), total_used)  # This is a hack until the values can be more accurately calcualted in EventTable.

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
    body = render_to_string("core/email/allocation_warning.html", Context(context))
    from_name, from_email = atmo_daemon_address()
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
    body = render_to_string("core/email/deploy_warning.html", Context(context))
    from_name, from_email = atmo_daemon_address()
    subject = '(%s) Preemptive Deploy Failure' % username
    return email_to_admin(subject, body, from_name, from_email,
                          admin_user='Atmosphere Alerts',
                          cc_user=False)


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
    body = render_to_string("core/email/deploy_failed.html",
                            context=Context(context))
    from_name, from_email = atmo_daemon_address()
    subject = '(%s) Deploy Failed' % username
    return email_to_admin(subject, body, from_name, from_email,
                          cc_user=False)


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
    body = render_to_string(
        "core/email/imaging_failed.html",
        context=Context(context))
    subject = 'ERROR - Atmosphere Imaging Task has encountered an exception'
    return email_to_admin(subject, body, user.username, user_email,
                          cc_user=False)


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
    body = render_to_string("core/email/imaging_success.html",
                            context=Context(context))
    subject = 'Your Atmosphere Image is Complete'
    return email_from_admin(user.username, subject, body)


def send_new_provider_email(username, identity):
    if not identity:
        raise Exception("Identity missing -- E-mail will not be sent")
    provider_name = identity.provider.location
    credential_list = identity.credential_set.all()
    email_template = get_email_template()
    subject = ("Your %s Atmosphere account has been granted access "
               "to the %s provider" % (settings.SITE_NAME, provider_name))
    context = {
        "new_provider_link": email_template.link_new_provider,
        "support_email": email_template.email_address,
        "support_email_header": email_template.email_header,
        "support_email_footer": email_template.email_footer,
        "user": username,
        "provider": provider_name,
        "credentials": credential_list,
    }
    body = render_to_string("core/email/provider_email.html",
                            context=Context(context))
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
    body = render_to_string("core/email/imaging_request.html",
                            context=Context(context))
    # Send staff url if not approved
    if not auto_approve:
        namespace = "api:v2:machinerequest-detail"
        base_url = reverse(namespace, args=(machine_request_id,))
        context["view"] = base_url
        context["approve"] = "%s/approve" % base_url
        context["deny"] = "%s/deny" % base_url
        staff_body = render_to_string("core/email/imaging_request_staff.html",
                                      context=Context(context))
        email_admin(request, subject, staff_body,
                    cc_user=False, request_tracker=True)

    return email_from_admin(user.username, subject, body)

def resource_request_email(request, username, quota, reason, options={}):
    """
    Processes Resource request. Sends email to the admins

    Returns a response.
    """
    user = User.objects.get(username=username)
    membership = IdentityMembership.objects.get(
        identity=user.select_identity(),
        member__in=user.group_set.all())
    admin_url = reverse('admin:core_identitymembership_change',
                        args=(membership.id,))

    # TODO: To enable joseph's admin_url this will need to be uncommented
    # See https://pods.iplantcollaborative.org/jira/browse/ATMO-1155
    #
    # if 'admin_url' in options:
    #     admin_url = options['admin_url']

    subject = "Atmosphere Resource Request - %s" % username
    context = {
        "quota": quota,
        "reason": reason,
        "url": request.build_absolute_uri(admin_url)
    }
    context.update(request_data(request))
    body = render_to_string("resource_request.html", context=context)
    success = email_admin(request, subject, body, cc_user=False, request_tracker=True)
    return {"email_sent": success}

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
