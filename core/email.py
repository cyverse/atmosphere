"""
Atmosphere core email.

"""
from datetime import datetime

from django.core.mail import EmailMessage
from atmosphere import settings
from atmosphere.logger import logger, email_logger

from auth.protocol.ldap import lookupEmail


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
    user = request.session.get('username', '')
    logger.debug("user = %s" % user)
    user_email = lookupEmail(user)
    if not user_email:
        user_email = "%s@iplantcollaborative.org" % user
    return (user, user_email)


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


def send_email(subject, body, from_email, to, cc=None, fail_silently=False):
    """ Use django.core.mail.EmailMessage to send and log an Atmosphere email.
    """
    try:
        msg = EmailMessage(subject=subject, body=body,
                           from_email=from_email,
                           to=to,
                           cc=cc)
        msg.send(fail_silently=fail_silently)
        email_logger.info("Email Sent."
                          + "To: %s\nFrom: %sCc: %s\nSubject: %s\nBody:\n%s" %
                         (from_email,
                          to,
                          cc,
                          subject,
                          body))
        return True
    except Exception as e:
        logger.error(e)
        return False


def email_admin(request, subject, message):
    """ Use request, subject and message to build and send a standard
        Atmosphere user request email. From an atmosphere user to admins.
        Returns True on success and False on failure.
    """
    user_agent, remote_ip, location, resolution = request_info(request)
    user, user_email = user_address(request)
    sendto, sendto_email = admin_address()
    # build email body.
    body = u"%s\nLocation: %s\nSent From: %s - %s\nSent By: %s - %s"
    body %= (message,
             location,
             user, remote_ip,
             user_agent, resolution)
    return send_email(subject, body,
                      from_email=email_address_str(user, user_email),
                      to=[email_address_str(sendto, sendto_email)],
                      cc=[email_address_str(user, user_email)])


def email_from_admin(user, subject, message):
    """ Use user, subject and message to build and send a standard
        Atmosphere admin email from admins to a user.
        Returns True on success and False on failure.
    """
    from_name, from_email = admin_address()
    user_email = lookupEmail(user)
    return send_email(subject, message,
                      from_email=email_address_str(from_name, from_email),
                      to=[email_address_str(user, user_email)],
                      cc=[email_address_str(from_name, user_email)])


def send_instance_email(user, instance_id, ip, linuxusername):
    """
    Sends an email to the user providing information about the new instance.

    Returns a boolean.
    """
    body = """
The atmosphere instance <%s> is running and ready for use.

Your Instance Information:
* IP Address: %s
* SSH Username: %s
* Launched at: %s

Please terminate instances when they are no longer needed.
This e-mail notification was auto-generated after instance launch.
Helpful links:
  Atmosphere Manual: Using Instances
  * https://pods.iplantcollaborative.org/wiki/display/atmman/Using+Instances
  Atmosphere E-mail Support
  * atmo@iplantcollaborative.org
""" % (instance_id,
       ip, linuxusername,
       datetime.now().strftime('%b, %d %Y %H:%M:%S'))
    subject = 'Your Atmosphere Instance is Available'
    return email_from_admin(user, subject, body)


def send_image_request_email(user, new_machine, name):
    """
    Sends an email to the user providing information about the new image.

    Returns a boolean
    """
    body = """Hello %s,

Your image is ready. The image ID is "%s" and the image is named "%s".

Thank you for using atmosphere!
If you have any questions please contact: support@iplantcollaborative.org""" %\
        (user.username, new_machine.identifier, name)
    subject = 'Your Atmosphere Image is Complete'
    return email_from_admin(user.username, subject, body)
