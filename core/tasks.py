# -*- coding: utf-8 -*-
"""
Core application tasks
"""

from celery.decorators import task

from django.core.mail import EmailMessage

from atmosphere import settings
from threepio import celery_logger, email_logger

from core.models.status_type import get_status_type

@task(name="send_email")
def send_email(subject, body, from_email, to, cc=None,
               fail_silently=False, html=False):
    """
    Use django.core.mail.EmailMessage to send and log an Atmosphere email.
    """

    try:
        msg = EmailMessage(subject=subject, body=body,
                           from_email=from_email,
                           to=to,
                           cc=cc)
        if html:
            msg.content_subtype = 'html'
        log_message = "\n> From:{0}\n> To:{1}\n> Cc:{2}\n> Subject:{3}\n> Body:\n{4}"
        args = (from_email, to, cc, subject, body)
        email_logger.info(log_message.format(*args))
        if getattr(settings, "SEND_EMAILS", True):
            msg.send(fail_silently=fail_silently)
            email_logger.info("NOTE: Above message sent successfully")
            celery_logger.info("NOTE: Above message sent successfully")
        else:
            email_logger.info("NOTE: Above message not sent -- SEND_EMAILS was False")
            celery_logger.info("NOTE: Above message not sent -- SEND_EMAILS was False")
        return True
    except Exception as e:
        celery_logger.exception(e)
        return False


@task(name="close_request")
def close_request(request):
    """
    Close the request and email approval message
    """
    request.status = get_status_type(status="closed")
    request.save()


@task(name='set_request_as_failed')
def set_request_as_failed(request):
    """
    Set the request as failed
    """
    request.status = get_status_type(status="failed")
    request.save()
