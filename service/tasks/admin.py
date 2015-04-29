from celery.decorators import task

from core.email import send_approved_quota_email
from core.models import QuotaRequest
from core.models.status_type import get_status_type

from service.quota import set_provider_quota as spq
from threepio import logger

@task(name="set_provider_quota",
      default_retry_delay=5,
      time_limit=30*60,  # 30minute hard-set time limit.
      max_retries=3)
def set_provider_quota(identity_uuid):
    try:
        spq(identity_uuid)
    except Exception as exc:
        logger.exception("Encountered an exception trying to 'set_provider_quota' for Identity UUID:%s" % identity_uuid)
        set_provider_quota.retry(exc=exc)


@task(name="close_quota_request")
def close_quota_request(res, identifier):
    """
    Close the request and email approval message
    """
    instance = QuotaRequest.objects.get(id=identifier)
    instance.status = get_status_type(status="closed")
    instance.save()
    send_approved_quota_email(user=instance.created_by,
                              request=instance.request,
                              reason=instance.admin_message)

@task(name='set_quota_request_failed')
def set_quota_request_failed(err, identifier):
    """
    Set the quota request as failed if
    Marks the quota request ask
    """
    request = QuotaRequest.objects.get(id=identifier)
    request.status = get_status_type(status="failed")
    request.save()
