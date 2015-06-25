"""
Atmosphere core email.

"""

from core.models import AtmosphereUser as User

from django.template import Context
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone

from pytz import timezone as pytz_timezone

from threepio import logger

from atmosphere import settings

from authentication.protocol.ldap import lookupEmail, lookupUser
from service.tasks.email import send_email as send_email_task


def send_email_template(subject, template, recipient, sender,
                        context=None, cc=None, html=True, silent=False):
    """
    Send an email using the template provided
    """
    body = render_to_string(template, context=Context(context))
    args = (subject, body, recipient, sender)
    kwargs = {
        "cc": cc,
        "fail_silently": silent,
        "html": html
    }
    send_email_task.apply_async(args=args, kwargs=kwargs)
    return True


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
    """ Return the username and email given a django request object.
    """
    try:
        username = request.session.get('username', '')
    except:
        pass
    if not username and hasattr(request, "user"):
        username = request.user.username
    return user_email_info(username)


def user_email_info(username):
    logger.debug("user = %s" % username)
    ldap_attrs = lookupUser(username)
    user_email = ldap_attrs.get('mail', [None])[0]
    if not user_email:
        raise Exception("Could not locate email address for User:%s - Attrs: %s" % (username, ldap_attrs))
    user_name = ldap_attrs.get('cn', [""])[0]
    if not user_name:
        user_name = "%s %s" % (ldap_attrs.get("displayName", [""])[0],
                               ldap_attrs.get("sn", [""])[0])
    if not user_name.strip(' '):
        user_name = username

    return (username, user_email, user_name)


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

def send_email(subject, body, from_email, to, cc=None,
               fail_silently=False, html=False):
    """
    Queue an email to be sent
    """
    args = (subject, body, from_email, to)
    kwargs = {
        "cc": cc,
        "fail_silently": fail_silently,
        "html": html
    }
    send_email_task.apply_async(args=args, kwargs=kwargs)
    return True


def email_admin(request, subject, message,
                cc_user=True, request_tracker=False):
    """ Use request, subject and message to build and send a standard
        Atmosphere user request email. From an atmosphere user to admins.
        Returns True on success and False on failure.
    """
    user_agent, remote_ip, location, resolution = request_info(request)
    user, user_email, user_name = lookup_user(request)
    # build email body.
    body = u"%s\nLocation: %s\nSent From: %s - %s\nSent By: %s - %s"
    body %= (message,
             location,
             user, remote_ip,
             user_agent, resolution)
    return email_to_admin(subject, body, user, user_email, cc_user=cc_user,
                          request_tracker=request_tracker)


def email_to_admin(subject, body, username=None,
                   user_email=None, cc_user=True, admin_user=None, request_tracker=False):
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
    #E-mail yourself if no users are provided
    if not username and not user_email:
        username, user_email = sendto, sendto_email
    elif not user_email:  # Username provided
        if type(username) == User:
            username = username.username
        user_email = lookupEmail(username)
        if not user_email:
            user_email = "%s@iplantcollaborative.org" % username
    elif not username:  # user_email provided
        username = 'Unknown'
    if request_tracker or not cc_user:
        #Send w/o the CC
        return send_email(subject, body,
                          from_email=email_address_str(username, user_email),
                          to=[email_address_str(sendto, sendto_email)])
    #Send w/ the CC
    return send_email(subject, body,
                      from_email=email_address_str(username, user_email),
                      to=[email_address_str(sendto, sendto_email)],
                      cc=[email_address_str(username, user_email)])


def email_from_admin(username, subject, message, html=False):
    """ Use user, subject and message to build and send a standard
        Atmosphere admin email from admins to a user.
        Returns True on success and False on failure.
    """
    from_name, from_email = admin_address()
    user_email = lookupEmail(username)
    if not user_email:
        user_email = "%s@iplantcollaborative.org" % username
    return send_email(subject, message,
                      from_email=email_address_str(from_name, from_email),
                      to=[email_address_str(username, user_email)],
                      cc=[email_address_str(from_name, from_email)],
                      html=html)


def send_approved_resource_email(user, request, reason):
    """
    Notify the user the that their request has been approved.
    """
    subject = "Your Resource Request has been approved"
    context = {
        "user": user.username,
        "request": request,
        "reason": reason
    }
    body = render_to_string("core/email/resource_request_approved.html",
                            context=Context(context))
    return email_from_admin(user, subject, body)


def send_denied_resource_email(user, request, reason):
    """
    Send an email notifying the user that their request has been denied.
    """
    subject = "Your Resource Request has been denied"
    context = {
        "user": user.username,
        "request": request,
        "reason": reason
    }
    body = render_to_string("core/email/resource_request_denied.html",
                            context=Context(context))
    return email_from_admin(user, subject, body)


def send_instance_email(username, instance_id, instance_name,
                        ip, launched_at, linuxusername):
    """
    Sends an email to the user providing information about the new instance.

    Returns a boolean.
    """
    format_string = '%b, %d %Y %H:%M:%S'
    username, user_email, user_name = user_email_info(user)
    launched_at = launched_at.replace(tzinfo=None)
    utc_date = django_timezone.make_aware(launched_at,
                                          timezone=pytz_timezone('UTC'))
    local_launched_at = django_timezone.localtime(utc_date)
    context = {
        "user": user_name,
        "id": instance_id,
        "name": instance_name,
        "ip": ip,
        "sshuser": linuxusername,
        "launched_at": launched_at.strftime(format_string),
        "local_launched_at": local_launched_at.strftime(format_string)
    }
    body = render_to_string("core/email/instance_ready.html", context=Context(context))
    subject = 'Your Atmosphere Instance is Available'
    return email_from_admin(username, subject, body)


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
    body = render_to_string("core/email/imaging_failed.html", context=Context(context))
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
    context = {
        "user": user_name,
        "identifier": new_machine.identifier,
        "alias": name
    }
    body = render_to_string("core/email/imaging_success.html",
                            context=Context(context))
    subject = 'Your Atmosphere Image is Complete'
    return email_from_admin(user.username, subject, body)

def send_new_provider_email(username, provider_name):
    subject = ("Your iPlant Atmosphere account has been granted access "
               "to the %s provider" % provider_name)
    context = {
        "user": username,
        "provider": provider_name,
    }
    body = render_to_string("core/email/provider_email.html",
                            context=Context(context))
    return email_from_admin(username, subject, body, html=True)
