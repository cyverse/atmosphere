# -*- coding: utf-8 -*-
"""
Core application tasks
"""

from celery.decorators import task

from django.core.mail import EmailMessage

from threepio import celery_logger, email_logger

from core.models import ResourceRequest
from core.models.status_type import get_status_type


log_message = "Email Sent. From:{0}\nTo:{1}Cc:{2}\nSubject:{3}\nBody:\n{4}"


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
        msg.send(fail_silently=fail_silently)
        args = (from_email, to, cc, subject, body)
        email_logger.info(log_message.format(*args))
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
