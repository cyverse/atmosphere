# -*- coding: utf-8 -*-
"""
Core application tasks
"""

from celery.decorators import task

from django.core.mail import EmailMessage
from django.utils import timezone

from atmosphere import settings
from threepio import celery_logger, email_logger

from core.models.status_type import get_status_type
from core.models.application import Application
from core.query import only_current_apps
from core.metrics.application import get_application_metrics


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
        email_logger.info("\n> From:%s\n> To:%s\n> Cc:%s\n> Subject:%s\n> Body:\n%s", from_email, to, cc, subject, body)
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


@task(name='generate_metrics')
def generate_metrics():
    nowtime = timezone.now()
    all_apps = Application.objects.filter(only_current_apps()).distinct().order_by('id')
    for app in all_apps:
        generate_metrics_for.apply_async(args=[app.id, app.name, nowtime])
    return True


@task(name='generate_metrics_for')
def generate_metrics_for(application_id, application_name, nowtime):
    app = Application.objects.get(id=application_id)
    app_metrics = get_application_metrics(app, nowtime)
    return app_metrics
