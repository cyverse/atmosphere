"""
Atmosphere core email.

"""
from datetime import datetime

from core.models import AtmosphereUser as User
from django.utils import timezone as django_timezone
from django.core.mail import EmailMessage

from pytz import timezone as pytz_timezone

from threepio import logger, email_logger

from atmosphere import settings

from authentication.protocol.ldap import lookupEmail


def email_address_str(name, email):
    """ Create an email address from a name and email.
    """
    return "%s <%s>" % (name, email)


def admin_address():
    """ Return the admin name and admin email from
        django's settings.
    """
    return (settings.ADMINS[0][0], settings.ADMINS[0][1])


def user_address(request):
    """ Return the username and email given a django request object.
    """
    logger.debug("request = %s" % str(request))
    username = request.session.get('username', '')
    logger.debug("user = %s" % username)
    user_email = lookupEmail(username)
    if not user_email:
        user_email = "%s@iplantcollaborative.org" % username
    return (username, user_email)


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
    """ Use django.core.mail.EmailMessage to send and log an Atmosphere email.
    """
    try:
        msg = EmailMessage(subject=subject, body=body,
                           from_email=from_email,
                           to=to,
                           cc=cc)
        if html:
            msg.content_subtype = 'html'
        msg.send(fail_silently=fail_silently)
        email_logger.info("Email Sent."
                          + "From:%s\nTo:%sCc:%s\nSubject:%s\nBody:\n%s" %
                         (from_email,
                          to,
                          cc,
                          subject,
                          body))
        return True
    except Exception as e:
        logger.error(e)
        return False


def email_admin(request, subject, message, cc_user=True):
    """ Use request, subject and message to build and send a standard
        Atmosphere user request email. From an atmosphere user to admins.
        Returns True on success and False on failure.
    """
    user_agent, remote_ip, location, resolution = request_info(request)
    user, user_email = user_address(request)
    # build email body.
    body = u"%s\nLocation: %s\nSent From: %s - %s\nSent By: %s - %s"
    body %= (message,
             location,
             user, remote_ip,
             user_agent, resolution)
    return email_to_admin(subject, body, user, user_email, cc_user=cc_user)


def email_to_admin(subject, body, username=None,
                   user_email=None, cc_user=True):
    """
    Send a basic email to the admins. Nothing more than subject and message
    are required.
    """
    sendto, sendto_email = admin_address()
    #E-mail yourself if no users are provided
    if not username and not user_email:
        username, user_email = username, user_email
    elif not user_email:  # Username provided
        user_email = lookupEmail(username)
    elif not username:  # user_email provided
        username = 'Unknown'
    if not cc_user:
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
    return send_email(subject, message,
                      from_email=email_address_str(from_name, from_email),
                      to=[email_address_str(username, user_email)],
                      cc=[email_address_str(from_name, from_email)],
                      html=html)


def send_instance_email(user, instance_id, instance_name,
                        ip, launched_at, linuxusername):
    """
    Sends an email to the user providing information about the new instance.

    Returns a boolean.
    """
    launched_at = launched_at.replace(tzinfo=None)
    body = """
The atmosphere instance <%s> is running and ready for use.

Your Instance Information:
* Name: %s
* IP Address: %s
* SSH Username: %s
* Launched at: %s UTC (%s Arizona time)

Please terminate instances when they are no longer needed.
This e-mail notification was auto-generated after instance launch.
Helpful links:
  Atmosphere Manual: Using Instances
  * https://pods.iplantcollaborative.org/wiki/display/atmman/Using+Instances
  Atmosphere E-mail Support
  * atmo@iplantcollaborative.org
""" % (instance_id,
       instance_name,
       ip, linuxusername,
       launched_at.strftime('%b, %d %Y %H:%M:%S'),
       django_timezone.localtime(
           django_timezone.make_aware(
               launched_at,
               timezone=pytz_timezone('UTC')))
       .strftime('%b, %d %Y %H:%M:%S'))
    subject = 'Your Atmosphere Instance is Available'
    return email_from_admin(user, subject, body)


def send_image_request_failed_email(machine_request, exception_str):
    """
    Sends an email to the admins, who will verify the reason for the error,
    with an option to re-approve the request.
    """
    user_email = lookupEmail(user.username)
    approve_link = '%s/api/v1/request_image/%s/approve' \
        % (settings.SERVER_URL, machine_request.id)
    body = """ADMINS: A machine request has FAILED."
Please look over the exception. If the exception is one-time failure
you can re-approve the image here: %s
------------------------------------------------------------------
Machine Request:
  ID: %d
  Owner: %s
  Instance: %s
  IP Address: %s
Exception: %s
""" % (approve_link, machine_request.id, machine_request.new_machine_owner,
        machine_request.instance.provider_alias, 
        machine_request.instance.ip_address,
        exception_str)
    subject = 'Your Atmosphere Image is Complete'
    return email_to_admin(subject, body, user.username, user_email,
                          cc_user=False)


def send_image_request_email(user, new_machine, name):
    """
    Sends an email to the admins, who will verify the image boots successfully.
    Upon launching, the admins will forward this email to the user,
    which will provide useful information about the new image.
    """
    user_email = lookupEmail(user.username)
    body = """Hello %s,

Your image is ready. The image ID is "%s" and the image is named "%s".

Thank you for using atmosphere!
If you have any questions please contact: support@iplantcollaborative.org""" %\
        (user.username, new_machine.identifier, name)
    subject = 'Your Atmosphere Image is Complete'
    return email_from_admin(user, subject, body)


def send_new_provider_email(username, provider_name):
    subject = "Your iPlant Atmosphere account has been granted access "\
              "to the %s provider" % provider_name
    django_user = User.objects.get(username=username)
    first_name = django_user.first_name
    help_link = "https://pods.iplantcollaborative.org/wiki/"\
                "display/atmman/Changing+Providers"
    ask_link = "http://ask.iplantcollaborative.org/"
    email_body = """Welcome %s,<br/><br/>
You have been granted access to the %s provider on Atmosphere.
Instructions to change to a new provider can be found on <a href="%s">this page</a>.
<br/>
<br/>
If you have questions or encounter technical issues while using %s, you can
browse and post questions to <a href="%s">iPlant Ask</a> or contact support@iplantcollaborative.org.
<br/>
Thank you,<br/>
iPlant Atmosphere Team""" % (first_name,
                             provider_name,
                             help_link,
                             provider_name,
                             ask_link)
    return email_from_admin(username, subject, email_body, html=True)
